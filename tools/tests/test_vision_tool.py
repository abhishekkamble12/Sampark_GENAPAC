"""
Unit tests for tools/vision_tool.py

All Vertex AI / Google Cloud SDK calls are mocked so these tests run without
a real GCP project or Vertex AI instance.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

# Mock sys.modules so the local imports inside VisionTool don't fail
mock_vertexai = MagicMock()
mock_generative_models = MagicMock()
sys.modules["vertexai"] = mock_vertexai
sys.modules["vertexai.generative_models"] = mock_generative_models

import pytest

import tools.vision_tool
from tools.vision_tool import VisionTool, _CAPTION_PROMPT, _MODEL_NAME
tools.vision_tool.vertexai = mock_vertexai
tools.vision_tool.GenerativeModel = mock_generative_models.GenerativeModel
tools.vision_tool.Part = mock_generative_models.Part
tools.vision_tool.Image = mock_generative_models.Image


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

PROJECT = "test-project"
LOCATION = "us-central1"
SAMPLE_IMAGE_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # minimal JPEG-like bytes


def _make_tool(mock_model: MagicMock) -> VisionTool:
    """Return a VisionTool and configure the global mock to return the mock_model."""
    mock_vertexai.reset_mock()
    mock_generative_models.reset_mock()
    mock_generative_models.GenerativeModel.return_value = mock_model
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
    tool = VisionTool(project_id="proj-a", location="europe-west1")

    assert tool._project_id == "proj-a"
    assert tool._location == "europe-west1"


def test_constructor_default_location():
    """Default location is ``us-central1``."""
    tool = VisionTool(project_id="proj-b")

    assert tool._location == "us-central1"


@pytest.mark.asyncio
async def test_caption_image_initialises_vertex_ai():
    """``vertexai.init`` is called with the supplied project and location."""
    tool = _make_tool(MagicMock())
    tool._project_id = "proj-c"
    tool._location = "us-east1"
    
    await tool.caption_image(SAMPLE_IMAGE_BYTES)

    mock_vertexai.init.assert_called_once_with(project="proj-c", location="us-east1")


@pytest.mark.asyncio
async def test_caption_image_instantiates_generative_model():
    """``GenerativeModel`` is instantiated with the expected model name."""
    tool = _make_tool(MagicMock())
    
    await tool.caption_image(SAMPLE_IMAGE_BYTES)

    mock_generative_models.GenerativeModel.assert_called_once_with(_MODEL_NAME)


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

    result = await tool.caption_image(SAMPLE_IMAGE_BYTES)

    assert result == "Cracked road surface with large pothole near a school entrance."


@pytest.mark.asyncio
async def test_caption_image_strips_whitespace():
    """Leading/trailing whitespace in the model response is stripped."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value = _make_response("\n  Some caption.\n  ")

    tool = _make_tool(mock_model)

    result = await tool.caption_image(SAMPLE_IMAGE_BYTES)

    assert result == "Some caption."


@pytest.mark.asyncio
async def test_caption_image_sends_prompt_to_model():
    """The community-infrastructure prompt is included in the generate_content call."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value = _make_response("A flooded street.")

    tool = _make_tool(mock_model)

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

    result = await tool.caption_image(SAMPLE_IMAGE_BYTES)

    assert result is None


@pytest.mark.asyncio
async def test_caption_image_returns_none_for_whitespace_only_text():
    """A whitespace-only response from the model returns ``None``."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value = _make_response("   \n\t  ")

    tool = _make_tool(mock_model)

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

    result = await tool.caption_image(SAMPLE_IMAGE_BYTES)

    assert result is None


@pytest.mark.asyncio
async def test_caption_image_returns_none_on_value_error():
    """A ``ValueError`` (e.g. content-policy violation) is caught; ``None`` returned."""
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = ValueError("Content policy violation")

    tool = _make_tool(mock_model)

    result = await tool.caption_image(SAMPLE_IMAGE_BYTES)

    assert result is None


@pytest.mark.asyncio
async def test_caption_image_returns_none_on_generic_exception():
    """Any unexpected exception is caught and ``None`` is returned."""
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = RuntimeError("unexpected SDK error")

    tool = _make_tool(mock_model)

    result = await tool.caption_image(SAMPLE_IMAGE_BYTES)

    assert result is None


@pytest.mark.asyncio
async def test_caption_image_returns_none_when_image_construction_fails():
    """If building the image Part raises, ``None`` is returned gracefully."""
    mock_model = MagicMock()

    tool = _make_tool(mock_model)

    mock_generative_models.Part.from_data.side_effect = ValueError("invalid image bytes")
    result = await tool.caption_image(b"not-an-image")
    mock_generative_models.Part.from_data.side_effect = None

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

    await tool.caption_image(SAMPLE_IMAGE_BYTES)

    call_args = mock_generative_models.Part.from_data.call_args
    assert call_args is not None
    assert call_args[1]["data"] == base64.b64encode(SAMPLE_IMAGE_BYTES).decode("utf-8")
