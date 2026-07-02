"""
tools/vision_tool.py — Vertex AI Vision tool for image captioning.
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


class VisionTool:
    """Async wrapper around Vertex AI Generative Models for image captioning.

    Args:
        project_id: GCP project ID.
        location:   Vertex AI region (default ``"us-central1"``).
        model_name: Gemini model name (default ``"gemini-1.5-flash"``).
    """

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "gemini-1.5-flash",
    ) -> None:
        self._project_id = project_id
        self._location = location
        self._model_name = model_name

    async def caption_image(self, image_bytes: bytes) -> str | None:
        """Generate a natural-language caption for the given image.

        The image is base64-encoded and sent to Gemini via Vertex AI.

        Args:
            image_bytes: Raw bytes of the image (JPEG, PNG, etc.).

        Returns:
            Caption string, or ``None`` on any failure.
        """
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
            import vertexai  # type: ignore[import-untyped]
            from vertexai.generative_models import GenerativeModel, Part  # type: ignore[import-untyped]

            vertexai.init(project=self._project_id, location=self._location)
            model = GenerativeModel(self._model_name)

            image_part = Part.from_data(
                data=base64.b64encode(image_bytes).decode("utf-8"),
                mime_type="image/jpeg",
            )
            response = model.generate_content([image_part, _CAPTION_PROMPT])
            text = response.text
            if not text or not text.strip():
                return None
            return text.strip()
        except Exception:
            logger.exception("Vertex AI caption_image failed")
            return None
