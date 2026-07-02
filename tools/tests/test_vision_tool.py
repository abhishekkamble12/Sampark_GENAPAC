"""
Unit tests for tools/vision_tool.py

All Vertex AI / Google Cloud SDK calls are mocked so these tests run without
a real GCP project or Vertex AI instance.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.vision_tool import VisionTool, _CAPTION_PROMPT, _MODEL_NAME


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

PROJECT = "test-project"
LOCATION = "us-central1"
SAMPLE_IMAGE_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # minimal JPEG-like bytes


def _make_tool(mock_model: MagicMock) -> VisionTool:
    """Return a VisionTool whose Vertex AI SDK calls are fully mocked."""
    with (
        patch("tools.vision_tool.vertexai.init"),
        patch("tools.vision_tool.GenerativeModel", return_value=mock_model),
    ):
        return VisionTool(project_id=PROJECT, location=LOCATION)


def _make_response(text: str) -> MagicMock:
    """Create a mock Vertex AI GenerateContentResponse with a given text."""
    response = MagicMock()
    response.text = text
    return response


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_constructor_stores_project_and_location():
    """Constructor stores project_id and location as instance attributes."""
    with (
        patch("tools.vision_tool.vertexai.init"),
        patch("tools.vision_tool.GenerativeModel"),
    ):
        tool = VisionTool(project_id="proj-a", location="europe-west1")

    assert tool._project_id == "proj-a"
    assert tool._location == "europe-west1"


def test_constructor_default_location():
    """Default location is ``us-central1``."""
    with (
        patch("tools.vision_tool.vertexai.init"),
        patch("tools.vision_tool.GenerativeModel"),
    ):
        tool = VisionTool(project_id="proj-b")

    assert tool._location == "us-central1"


def test_constructor_initialises_vertex_ai():
    """``vertexai.init`` is called with the supplied project and location."""
    with (
        patch("tools.vision_tool.vertexai.init") as mock_init,
        patch("tools.vision_tool.GenerativeModel"),
    ):
        VisionTool(project_id="proj-c", location="us-east1")

    mock_init.assert_called_once_with(project="proj-c", location="us-east1")


def test_constructor_instantiates_generative_model():
    """``GenerativeModel`` is instantiated with the expected model name."""
    with (
        patch("tools.vision_tool.vertexai.init"),
        patch("tools.vision_tool.GenerativeModel") as mock_gm,
    ):
        VisionTool(project_id="proj-d")

    mock_gm.assert_called_once_with(_MODEL_NAME)


# ---------------------------------------------------------------------------
# caption_image — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_caption_image_returns_text_on_success():
    """A successful model response returns the caption string."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value = _make_response(
        "  Cracked road surface with large pothole near a school entrance.  "
    )

    tool = _make_tool(mock_model)

    with (
        patch("tools.vision_tool.Part.from_image"),
        patch("tools.vision_tool.Image.from_bytes"),
    ):
        result = await tool.caption_image(SAMPLE_IMAGE_BYTES)

    assert result == "Cracked road surface with large pothole near a school entrance."


@pytest.mark.asyncio
async def test_caption_image_strips_whitespace():
    """Leading/trailing whitespace in the model response is stripped."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value = _make_response("\n  Some caption.\n  ")

    tool = _make_tool(mock_model)

    with (
        patch("tools.vision_tool.Part.from_image"),
        patch("tools.vision_tool.Image.from_bytes"),
    ):
        result = await tool.caption_image(SAMPLE_IMAGE_BYTES)

    assert result == "Some caption."


@pytest.mark.asyncio
async def test_caption_image_sends_prompt_to_model():
    """The community-infrastructure prompt is included in the generate_content call."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value = _make_response("A flooded street.")

    tool = _make_tool(mock_model)

    with (
        patch("tools.vision_tool.Part.from_image"),
        patch("tools.vision_tool.Image.from_bytes"),
    ):
        await tool.caption_image(SAMPLE_IMAGE_BYTES)

    call_args = mock_model.generate_content.call_args
    content_list = call_args[0][0]
    # The prompt string must appear somewhere in the content list
    assert any(_CAPTION_PROMPT in str(item) for item in content_list)


# ---------------------------------------------------------------------------
# caption_image — empty / blank responses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_caption_image_returns_none_for_empty_text():
    """An empty string response from the model returns ``None``."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value = _make_response("")

    tool = _make_tool(mock_model)

    with (
        patch("tools.vision_tool.Part.from_image"),
        patch("tools.vision_tool.Image.from_bytes"),
    ):
        result = await tool.caption_image(SAMPLE_IMAGE_BYTES)

    assert result is None


@pytest.mark.asyncio
async def test_caption_image_returns_none_for_whitespace_only_text():
    """A whitespace-only response from the model returns ``None``."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value = _make_response("   \n\t  ")

    tool = _make_tool(mock_model)

    with (
        patch("tools.vision_tool.Part.from_image"),
        patch("tools.vision_tool.Image.from_bytes"),
    ):
        result = await tool.caption_image(SAMPLE_IMAGE_BYTES)

    assert result is None


# ---------------------------------------------------------------------------
# caption_image — error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_caption_image_returns_none_on_google_api_error():
    """A ``GoogleAPIError`` from the model is caught; ``None`` is returned."""
    from google.api_core import exceptions as google_exceptions

    mock_model = MagicMock()
    mock_model.generate_content.side_effect = google_exceptions.GoogleAPIError(
        "Vertex AI unavailable"
    )

    tool = _make_tool(mock_model)

    with (
        patch("tools.vision_tool.Part.from_image"),
        patch("tools.vision_tool.Image.from_bytes"),
    ):
        result = await tool.caption_image(SAMPLE_IMAGE_BYTES)

    assert result is None


@pytest.mark.asyncio
async def test_caption_image_returns_none_on_value_error():
    """A ``ValueError`` (e.g. content-policy violation) is caught; ``None`` returned."""
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = ValueError("Content policy violation")

    tool = _make_tool(mock_model)

    with (
        patch("tools.vision_tool.Part.from_image"),
        patch("tools.vision_tool.Image.from_bytes"),
    ):
        result = await tool.caption_image(SAMPLE_IMAGE_BYTES)

    assert result is None


@pytest.mark.asyncio
async def test_caption_image_returns_none_on_generic_exception():
    """Any unexpected exception is caught and ``None`` is returned."""
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = RuntimeError("unexpected SDK error")

    tool = _make_tool(mock_model)

    with (
        patch("tools.vision_tool.Part.from_image"),
        patch("tools.vision_tool.Image.from_bytes"),
    ):
        result = await tool.caption_image(SAMPLE_IMAGE_BYTES)

    assert result is None


@pytest.mark.asyncio
async def test_caption_image_returns_none_when_image_construction_fails():
    """If building the image Part raises, ``None`` is returned gracefully."""
    mock_model = MagicMock()

    tool = _make_tool(mock_model)

    with (
        patch(
            "tools.vision_tool.Image.from_bytes",
            side_effect=ValueError("invalid image bytes"),
        ),
        patch("tools.vision_tool.Part.from_image"),
    ):
        result = await tool.caption_image(b"not-an-image")

    assert result is None


# ---------------------------------------------------------------------------
# caption_image — base64 encoding
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_caption_image_base64_encodes_bytes():
    """Image bytes are Base64-encoded before being used in the request."""
    import base64

    mock_model = MagicMock()
    mock_model.generate_content.return_value = _make_response("Infrastructure caption.")

    tool = _make_tool(mock_model)

    captured_calls = []

    def fake_from_bytes(data: bytes) -> MagicMock:
        captured_calls.append(data)
        return MagicMock()

    with (
        patch("tools.vision_tool.Image.from_bytes", side_effect=fake_from_bytes),
        patch("tools.vision_tool.Part.from_image", return_value=MagicMock()),
    ):
        await tool.caption_image(SAMPLE_IMAGE_BYTES)

    # Image.from_bytes should have been called with the original raw bytes
    assert len(captured_calls) == 1
    assert captured_calls[0] == SAMPLE_IMAGE_BYTES
