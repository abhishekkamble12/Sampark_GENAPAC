"""
tools/vision_tool.py — Gemini Vision Tool (FREE via Google AI Studio)

Replaces Vertex AI Vision with direct Gemini API calls.
No GCP billing required — uses free Gemini API key from AI Studio.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

logger = logging.getLogger(__name__)

_CAPTION_PROMPT = (
    "Describe this image in detail. Focus on any community infrastructure issues, "
    "damage, or problems visible. Be specific about location features."
)
_MODEL_NAME = "gemini-1.5-flash"


class VisionTool:
    """Async wrapper around Gemini API for image captioning.

    Uses free Gemini API (AI Studio) — no Vertex AI or GCP required.

    Args:
        gemini_model: Gemini GenerativeModel instance from google.generativeai.
        model_name:   Gemini model name to use.
    """

    def __init__(
        self,
        gemini_model: Any = None,
        model_name: str = _MODEL_NAME,
    ) -> None:
        self._gemini_model = gemini_model
        self._model_name = model_name

    async def caption_image(self, image_bytes: bytes) -> str | None:
        """Generate a natural-language caption for the given image.

        Uses Gemini API (free) instead of Vertex AI Vision.

        Args:
            image_bytes: Raw bytes of the image (JPEG, PNG, etc.).

        Returns:
            Caption string, or ``None`` on any failure.
        """
        if self._gemini_model is None:
            # Mock mode for testing
            return "A damaged road with visible cracks and water puddles."

        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None, self._sync_caption_image, image_bytes
            )
        except Exception:
            logger.exception("caption_image failed")
            return None

    def _sync_caption_image(self, image_bytes: bytes) -> str | None:
        """Blocking implementation — runs inside a thread executor."""
        try:
            import google.generativeai as genai
            from google.generativeai import GenerativeModel

            # Reuse the existing model or create a new one
            if self._gemini_model is not None:
                model = self._gemini_model
            else:
                model = GenerativeModel(self._model_name)

            image_part = {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            }

            response = model.generate_content([image_part, _CAPTION_PROMPT])
            text = response.text if hasattr(response, "text") else str(response)
            if not text or not text.strip():
                return None
            return text.strip()
        except Exception:
            logger.exception("Gemini Vision caption_image failed")
            return None
