"""
Property-based tests for agents.intake_agent.

**Validates: Requirements 4.7**

Property under test:
    For any text input supplied to ``intake_node``, the resulting
    ``issue.type`` always belongs to ``KNOWN_ISSUE_TYPES``
    (the 8 canonical categories: road, sanitation, water, electricity,
    flood, traffic, health, other).

Uses the ``hypothesis`` library as specified in design.md §11 and tasks.md notes.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from agents.intake_agent import make_intake_node, _classify_type
from agents.state import KNOWN_ISSUE_TYPES, GraphState

# ---------------------------------------------------------------------------
# Stub helpers (same pattern as unit tests — no real API calls)
# ---------------------------------------------------------------------------


class _PassthroughSpeechTool:
    """Never called during text-modality tests, but satisfies the interface."""

    async def transcribe(self, audio_bytes: bytes) -> str | None:  # noqa: ARG002
        return None


class _PassthroughVisionTool:
    """Never called during text-modality tests, but satisfies the interface."""

    async def caption_image(self, image_bytes: bytes) -> str | None:  # noqa: ARG002
        return None


class _ParametricGeminiModel:
    """Gemini stub that returns a configurable extracted type.

    The language-detection call (call #1) always returns English.
    The extraction call (call #2) returns the ``raw_type`` passed at construction.
    """

    def __init__(self, raw_type: str) -> None:
        self._raw_type = raw_type
        self._call_count = 0

    def generate_content(self, prompt: str) -> object:  # noqa: ARG002
        self._call_count += 1

        if self._call_count == 1:
            # Language detection response
            payload = {"language": "en", "is_english": True, "translated_text": ""}
        else:
            # Entity extraction response
            payload = {
                "type": self._raw_type,
                "location": "Test Location",
                "description": "A test issue description.",
            }

        class _Response:
            text = json.dumps(payload)

        return _Response()


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Mix of known canonical types, common synonyms, and arbitrary strings
_raw_issue_types = st.one_of(
    st.sampled_from(sorted(KNOWN_ISSUE_TYPES)),
    st.sampled_from([
        "pothole", "garbage", "pipe leak", "blackout", "flooding",
        "congestion", "hospital", "rubbish", "outage", "drainage",
        "traffic jam", "water shortage", "road damage",
    ]),
    st.text(min_size=0, max_size=40),  # completely arbitrary
)

_text_queries = st.text(min_size=1, max_size=200).filter(
    lambda s: not s.startswith("audio:") and not s.startswith("image:")
)


def _make_state(query: str) -> GraphState:
    return {
        "query": query,
        "user": {
            "user_id": "u_pbt",
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
            "session_id": "sess_pbt",
            "status": "running",
            "retry_count": 0,
            "node_checkpoints": [],
        },
    }


# ---------------------------------------------------------------------------
# Property 1 — _classify_type always returns a known category
# ---------------------------------------------------------------------------


@given(raw_type=_raw_issue_types)
@settings(max_examples=500)
def test_classify_type_always_returns_known_category(raw_type: str) -> None:
    """``_classify_type`` must always return a member of KNOWN_ISSUE_TYPES.

    **Validates: Requirements 4.7**
    """
    result = _classify_type(raw_type)
    assert result in KNOWN_ISSUE_TYPES, (
        f"_classify_type({raw_type!r}) returned {result!r}, which is not in "
        f"KNOWN_ISSUE_TYPES={sorted(KNOWN_ISSUE_TYPES)}"
    )


# ---------------------------------------------------------------------------
# Property 2 — intake_node always produces issue.type ∈ KNOWN_ISSUE_TYPES
# ---------------------------------------------------------------------------


@given(
    query=_text_queries,
    raw_type=_raw_issue_types,
)
@settings(max_examples=200)
def test_intake_node_issue_type_always_canonical(query: str, raw_type: str) -> None:
    """For any text input, ``issue.type`` always belongs to ``KNOWN_ISSUE_TYPES``.

    **Validates: Requirements 4.7**

    The Gemini model is stubbed to return ``raw_type``; the intake node must
    classify it into one of the 8 canonical categories regardless of what the
    raw extraction says.
    """
    node = make_intake_node(
        speech_tool=_PassthroughSpeechTool(),
        vision_tool=_PassthroughVisionTool(),
        gemini_model=_ParametricGeminiModel(raw_type=raw_type),
    )
    state = _make_state(query)

    result_state = asyncio.run(node(state))

    # If there was a timeout or other intake error, issue may be None —
    # but the error must be a known error string, not a crash.
    if result_state.get("intake_error") is not None:
        assert isinstance(result_state["intake_error"], str), (
            "intake_error must be a string"
        )
        return  # No issue produced — acceptable when there is an intake error

    assert result_state["issue"] is not None, (
        f"issue should be set for text query={query!r}, raw_type={raw_type!r}"
    )
    issue_type = result_state["issue"]["type"]
    assert issue_type in KNOWN_ISSUE_TYPES, (
        f"issue.type={issue_type!r} is not in KNOWN_ISSUE_TYPES for "
        f"query={query!r}, raw_type={raw_type!r}"
    )
