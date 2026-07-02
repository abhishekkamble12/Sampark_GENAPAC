"""
tools/speech_tool.py — Vertex AI Speech-to-Text tool for audio transcription.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class SpeechTool:
    """Async wrapper around the Google Cloud Speech-to-Text v2 API.

    Args:
        project_id: GCP project ID.
        location:   Speech API region (default ``"us-central1"``).
    """

    def __init__(self, project_id: str, location: str = "us-central1") -> None:
        self._project_id = project_id
        self._location = location

    async def transcribe(
        self, audio_bytes: bytes, language_code: str = "en-IN"
    ) -> str | None:
        """Transcribe audio bytes to text using Speech-to-Text v2.

        Args:
            audio_bytes:   Raw audio content (MP3, OGG, WAV, etc.).
            language_code: BCP-47 language code (default ``"en-IN"``).

        Returns:
            Full transcript string, or ``None`` on any failure.
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None, self._sync_transcribe, audio_bytes, language_code
            )
        except Exception:
            logger.exception("transcribe failed")
            return None

    def _sync_transcribe(self, audio_bytes: bytes, language_code: str) -> str | None:
        """Blocking implementation — runs inside a thread executor."""
        try:
            from google.cloud.speech_v2 import SpeechClient  # type: ignore[import-untyped]
            from google.cloud.speech_v2.types import cloud_speech  # type: ignore[import-untyped]

            client = SpeechClient()
            recognizer = (
                f"projects/{self._project_id}/locations/{self._location}/recognizers/_"
            )
            config = cloud_speech.RecognitionConfig(
                auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                language_codes=[language_code],
                model="long",
            )
            request = cloud_speech.RecognizeRequest(
                recognizer=recognizer,
                config=config,
                content=audio_bytes,
            )
            response = client.recognize(request=request)

            transcript_parts: list[str] = []
            for result in response.results:
                if result.alternatives:
                    transcript_parts.append(result.alternatives[0].transcript)

            transcript = " ".join(transcript_parts).strip()
            return transcript if transcript else None

        except Exception:
            logger.exception("Speech-to-Text v2 transcribe failed")
            return None
