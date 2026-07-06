"""
Unit tests for tools/vision_tool.py

The new VisionTool uses Gemini API directly (free via AI Studio).
All tests run without any GCP dependencies.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.vision_tool import VisionTool


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

SAMPLE_IMAGE_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100


class _MockGeminiResponse:
    def __init__(self, text: str):
        self.text = text


class _MockGeminiModel:
    def __init__(self, text: str = "Cracked road surface with large pothole.", should_fail: bool = False):
        self._text = text
        self._should_fail = should_fail

    def generate_content(self, content_list) -> _MockGeminiResponse:
        if self._should_fail:
            raise ValueError("Content policy violation")
        return _MockGeminiResponse(self._text)


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_constructor_accepts_gemini_model():
    """Constructor stores the gemini_model reference."""
    model = _MockGeminiModel()
    tool = VisionTool(gemini_model=model, model_name="gemini-1.5-flash")
    assert tool._gemini_model is model
    assert tool._model_name == "gemini-1.5-flash"


# ---------------------------------------------------------------------------
# caption_image — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_caption_image_returns_text():
    """A successful model response returns the caption string."""
    model = _MockGeminiModel(text="  Cracked road surface with large pothole near a school.  ")
    tool = VisionTool(gemini_model=model)

    result = await tool.caption_image(SAMPLE_IMAGE_BYTES)

    assert result == "Cracked road surface with large pothole near a school."


@pytest.mark.asyncio
async def test_caption_image_strips_whitespace():
    """Leading/trailing whitespace in the response is stripped."""
    model = _MockGeminiModel(text="\n  Some caption.\n  ")
    tool = VisionTool(gemini_model=model)

    result = await tool.caption_image(SAMPLE_IMAGE_BYTES)
    assert result == "Some caption."


@pytest.mark.asyncio
async def test_caption_image_mock_mode():
    """When gemini_model is None, returns a mock caption."""
    tool = VisionTool(gemini_model=None)
    result = await tool.caption_image(SAMPLE_IMAGE_BYTES)
    assert result is not None
    assert "road" in result.lower()


# ---------------------------------------------------------------------------
# caption_image — error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_caption_image_returns_none_on_failure():
    """Any exception is caught and None is returned."""
    model = _MockGeminiModel(should_fail=True)
    tool = VisionTool(gemini_model=model)

    result = await tool.caption_image(SAMPLE_IMAGE_BYTES)
    assert result is None
