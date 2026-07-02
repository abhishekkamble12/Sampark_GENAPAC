"""
Unit tests for agents.intake_agent — covering all eight scenarios specified
in task 4.9.

Scenarios tested:
1.  Text modality happy path
2.  Audio modality happy path
3.  Image modality happy path
4.  Audio failure → intake_error = "audio_unprocessable"
5.  Image failure → intake_error = "image_unclassifiable"
6.  Missing location → extraction_error = True
7.  Non-English text → translation performed, original_language set
8.  Unknown issue type → classified as "other"

All external dependencies (SpeechTool, VisionTool, Gemini model) are replaced
with lightweight synchronous fakes so no real API calls are made.
"""

from __future__ import annotations

import json
import pytest

from agents.intake_agent import make_intake_node, _classify_type, _detect_modality
from agents.state import KNOWN_ISSUE_TYPES, GraphState


# ---------------------------------------------------------------------------
# Fake / stub helpers
# ---------------------------------------------------------------------------


class _FakeSpeechTool:
    """Stub SpeechTool whose behaviour is controlled by constructor args."""

    def __init__(self, transcript: str | None = "There is a large pothole on MG Road."):
        self._transcript = transcript

    async def transcribe(self, audio_bytes: bytes) -> str | None:  # noqa: ARG002
        return self._transcript


class _FakeVisionTool:
    """Stub VisionTool whose behaviour is controlled by constructor args."""

    def __init__(self, caption: str | None = "A broken road with a pothole near MG Road."):
        self._caption = caption

    async def caption_image(self, image_bytes: bytes) -> str | None:  # noqa: ARG002
        return self._caption


class _FakeGeminiResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeGeminiModel:
    """Stub Gemini model.  Call sequences are configurable."""

    def __init__(
        self,
        lang_response: dict | None = None,
        extract_response: dict | None = None,
    ) -> None:
        # Default responses mimic what Gemini would produce
        self._lang = lang_response or {
            "language": "en",
            "is_english": True,
            "translated_text": "",
        }
        self._extract = extract_response or {
            "type": "road",
            "location": "MG Road",
            "description": "Large pothole near school gate.",
        }
        self._call_count = 0

    def generate_content(self, prompt: str) -> _FakeGeminiResponse:
        self._call_count += 1
        # First call → language detection; second call → entity extraction
        if self._call_count == 1:
            return _FakeGeminiResponse(json.dumps(self._lang))
        return _FakeGeminiResponse(json.dumps(self._extract))


# ---------------------------------------------------------------------------
# State builder helper
# ---------------------------------------------------------------------------


def _make_state(
    query: str = "There is a large pothole on MG Road.",
    user: dict | None = None,
) -> GraphState:
    return {
        "query": query,
        "user": user or {
            "user_id": "u1",
            "role": "citizen",
            "ward_ids": ["w1"],
            "preferred_channel": "email",
        },
        "issue": None,
        "validation": None,
        "context": None,
        "analytics": None,
        "prediction": None,
        "rag_chunks": None,
        "recommendation": None,
        "workflow": None,
        "response": None,
        "intake_error": None,
        "translation_error": False,
        "extraction_error": False,
        "no_policy_context": False,
        "execution": {
            "session_id": "sess_test",
            "status": "running",
            "retry_count": 0,
            "node_checkpoints": [],
        },
    }


# ===========================================================================
# Scenario 1: Text modality happy path
# ===========================================================================


@pytest.mark.asyncio
async def test_text_modality_happy_path():
    """Plain text input should produce a populated IssueObject with no errors."""
    node = make_intake_node(
        speech_tool=_FakeSpeechTool(),
        vision_tool=_FakeVisionTool(),
        gemini_model=_FakeGeminiModel(
            extract_response={
                "type": "road",
                "location": "MG Road",
                "description": "Large pothole near school gate.",
            }
        ),
    )
    state = _make_state(query="There is a large pothole on MG Road.")
    result = await node(state)

    assert result["intake_error"] is None
    assert result["extraction_error"] is False
    assert result["issue"] is not None
    issue = result["issue"]
    assert issue["type"] in KNOWN_ISSUE_TYPES
    assert issue["type"] == "road"
    assert issue["location"] is not None
    assert "MG Road" in issue["location"]["address"]
    assert isinstance(issue["description"], str)
    assert len(issue["description"]) > 0


# ===========================================================================
# Scenario 2: Audio modality happy path
# ===========================================================================


@pytest.mark.asyncio
async def test_audio_modality_happy_path():
    """audio: prefix triggers SpeechTool and produces a valid IssueObject."""
    node = make_intake_node(
        speech_tool=_FakeSpeechTool(transcript="Flooding on Station Road near the market."),
        vision_tool=_FakeVisionTool(),
        gemini_model=_FakeGeminiModel(
            extract_response={
                "type": "flood",
                "location": "Station Road",
                "description": "Flooding near the market.",
            }
        ),
    )
    state = _make_state(query="audio:<binary-audio-data>")
    result = await node(state)

    assert result["intake_error"] is None
    assert result["issue"] is not None
    assert result["issue"]["type"] == "flood"
    assert result["issue"]["location"] is not None


# ===========================================================================
# Scenario 3: Image modality happy path
# ===========================================================================


@pytest.mark.asyncio
async def test_image_modality_happy_path():
    """image: prefix triggers VisionTool and produces a valid IssueObject."""
    node = make_intake_node(
        speech_tool=_FakeSpeechTool(),
        vision_tool=_FakeVisionTool(caption="Overflowing garbage bins on Park Street."),
        gemini_model=_FakeGeminiModel(
            extract_response={
                "type": "sanitation",
                "location": "Park Street",
                "description": "Overflowing garbage bins.",
            }
        ),
    )
    state = _make_state(query="image:<binary-image-data>")
    result = await node(state)

    assert result["intake_error"] is None
    assert result["issue"] is not None
    assert result["issue"]["type"] == "sanitation"


# ===========================================================================
# Scenario 4: Audio failure → intake_error = "audio_unprocessable"
# ===========================================================================


@pytest.mark.asyncio
async def test_audio_failure_sets_intake_error():
    """When SpeechTool.transcribe returns None, intake_error is set."""
    node = make_intake_node(
        speech_tool=_FakeSpeechTool(transcript=None),
        vision_tool=_FakeVisionTool(),
        gemini_model=_FakeGeminiModel(),
    )
    state = _make_state(query="audio:<corrupt-audio>")
    result = await node(state)

    assert result["intake_error"] == "audio_unprocessable"
    assert result["issue"] is None


@pytest.mark.asyncio
async def test_audio_exception_sets_intake_error():
    """When SpeechTool.transcribe raises, intake_error is set."""

    class _RaisingSpeechTool:
        async def transcribe(self, audio_bytes: bytes) -> str | None:
            raise RuntimeError("Speech API unavailable")

    node = make_intake_node(
        speech_tool=_RaisingSpeechTool(),
        vision_tool=_FakeVisionTool(),
        gemini_model=_FakeGeminiModel(),
    )
    state = _make_state(query="audio:<corrupt-audio>")
    result = await node(state)

    assert result["intake_error"] == "audio_unprocessable"
    assert result["issue"] is None


# ===========================================================================
# Scenario 5: Image failure → intake_error = "image_unclassifiable"
# ===========================================================================


@pytest.mark.asyncio
async def test_image_failure_sets_intake_error():
    """When VisionTool.caption_image returns None, intake_error is set."""
    node = make_intake_node(
        speech_tool=_FakeSpeechTool(),
        vision_tool=_FakeVisionTool(caption=None),
        gemini_model=_FakeGeminiModel(),
    )
    state = _make_state(query="image:<corrupt-image>")
    result = await node(state)

    assert result["intake_error"] == "image_unclassifiable"
    assert result["issue"] is None


@pytest.mark.asyncio
async def test_image_exception_sets_intake_error():
    """When VisionTool.caption_image raises, intake_error is set."""

    class _RaisingVisionTool:
        async def caption_image(self, image_bytes: bytes) -> str | None:
            raise RuntimeError("Vision API unavailable")

    node = make_intake_node(
        speech_tool=_FakeSpeechTool(),
        vision_tool=_RaisingVisionTool(),
        gemini_model=_FakeGeminiModel(),
    )
    state = _make_state(query="image:<corrupt-image>")
    result = await node(state)

    assert result["intake_error"] == "image_unclassifiable"
    assert result["issue"] is None


# ===========================================================================
# Scenario 6: Missing location → extraction_error = True
# ===========================================================================


@pytest.mark.asyncio
async def test_missing_location_sets_extraction_error():
    """Extraction response without a location sets extraction_error and location=None."""
    node = make_intake_node(
        speech_tool=_FakeSpeechTool(),
        vision_tool=_FakeVisionTool(),
        gemini_model=_FakeGeminiModel(
            extract_response={
                "type": "road",
                "location": None,
                "description": "Pothole somewhere.",
            }
        ),
    )
    state = _make_state(query="There is a pothole somewhere.")
    result = await node(state)

    assert result["extraction_error"] is True
    assert result["issue"] is not None
    assert result["issue"]["location"] is None


@pytest.mark.asyncio
async def test_empty_location_string_sets_extraction_error():
    """An empty location string is treated as absent."""
    node = make_intake_node(
        speech_tool=_FakeSpeechTool(),
        vision_tool=_FakeVisionTool(),
        gemini_model=_FakeGeminiModel(
            extract_response={
                "type": "road",
                "location": "",
                "description": "Pothole somewhere.",
            }
        ),
    )
    state = _make_state(query="There is a pothole somewhere.")
    result = await node(state)

    assert result["extraction_error"] is True
    assert result["issue"]["location"] is None  # type: ignore[index]


# ===========================================================================
# Scenario 7: Non-English text → translation performed
# ===========================================================================


@pytest.mark.asyncio
async def test_non_english_text_is_translated():
    """Hindi input causes translation; original_language is set and no translation_error."""
    # First Gemini call (lang detection) returns Hindi; second (extraction) uses translated text.
    gemini = _FakeGeminiModel(
        lang_response={
            "language": "hi",
            "is_english": False,
            "translated_text": "There is a large pothole on MG Road.",
        },
        extract_response={
            "type": "road",
            "location": "MG Road",
            "description": "Large pothole.",
        },
    )
    node = make_intake_node(
        speech_tool=_FakeSpeechTool(),
        vision_tool=_FakeVisionTool(),
        gemini_model=gemini,
    )
    state = _make_state(query="MG Road par ek bada gadda hai.")
    result = await node(state)

    assert result["translation_error"] is False
    assert result["issue"] is not None
    assert result["issue"]["original_language"] == "hi"


@pytest.mark.asyncio
async def test_unsupported_language_sets_translation_error():
    """Unknown language sets translation_error = True."""
    gemini = _FakeGeminiModel(
        lang_response={
            "language": "unknown",
            "is_english": False,
            "translated_text": "",
        },
        extract_response={
            "type": "road",
            "location": None,
            "description": "Something.",
        },
    )
    node = make_intake_node(
        speech_tool=_FakeSpeechTool(),
        vision_tool=_FakeVisionTool(),
        gemini_model=gemini,
    )
    state = _make_state(query="Qwerty lorem ipsum.")
    result = await node(state)

    assert result["translation_error"] is True


# ===========================================================================
# Scenario 8: Unknown issue type → classified as "other"
# ===========================================================================


@pytest.mark.asyncio
async def test_unknown_issue_type_classified_as_other():
    """Gemini returning an unrecognised type results in issue.type == 'other'."""
    node = make_intake_node(
        speech_tool=_FakeSpeechTool(),
        vision_tool=_FakeVisionTool(),
        gemini_model=_FakeGeminiModel(
            extract_response={
                "type": "flying_saucer_sighting",
                "location": "Central Park",
                "description": "Very unusual event.",
            }
        ),
    )
    state = _make_state(query="Something very unusual happened in Central Park.")
    result = await node(state)

    assert result["issue"] is not None
    assert result["issue"]["type"] == "other"


# ===========================================================================
# Unit tests for helper functions (isolated)
# ===========================================================================


class TestClassifyType:
    """Tests for the ``_classify_type`` function."""

    def test_exact_known_types_pass_through(self):
        for t in KNOWN_ISSUE_TYPES:
            assert _classify_type(t) == t

    def test_case_insensitive_exact_match(self):
        assert _classify_type("Road") == "road"
        assert _classify_type("FLOOD") == "flood"

    def test_pothole_maps_to_road(self):
        assert _classify_type("pothole") == "road"

    def test_garbage_maps_to_sanitation(self):
        assert _classify_type("garbage") == "sanitation"

    def test_pipe_leak_maps_to_water(self):
        assert _classify_type("pipe leak") == "water"

    def test_blackout_maps_to_electricity(self):
        assert _classify_type("blackout") == "electricity"

    def test_flooding_maps_to_flood(self):
        assert _classify_type("flooding") == "flood"

    def test_congestion_maps_to_traffic(self):
        assert _classify_type("congestion") == "traffic"

    def test_hospital_maps_to_health(self):
        assert _classify_type("hospital") == "health"

    def test_unknown_type_returns_other(self):
        assert _classify_type("flying_saucer_sighting") == "other"
        assert _classify_type("") == "other"
        assert _classify_type("   ") == "other"


class TestDetectModality:
    """Tests for the ``_detect_modality`` function."""

    def test_audio_prefix_detected(self):
        assert _detect_modality("audio:<bytes>", {}) == "audio"

    def test_image_prefix_detected(self):
        assert _detect_modality("image:<bytes>", {}) == "image"

    def test_plain_text_detected(self):
        assert _detect_modality("There is a pothole on MG Road.", {}) == "text"

    def test_user_modality_hint_audio(self):
        assert _detect_modality("some data", {"modality": "audio"}) == "audio"

    def test_user_modality_hint_image(self):
        assert _detect_modality("some data", {"modality": "image"}) == "image"

    def test_audio_prefix_takes_precedence_over_user_hint(self):
        assert _detect_modality("audio:<data>", {"modality": "image"}) == "audio"
