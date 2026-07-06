"""
tools/speech_tool.py — Speech Transcription Tool (FREE - No GCP needed)

Speech-to-Text is handled client-side via the Browser Web Speech API.
This backend tool provides a mock for testing; real transcription happens
in the browser.

Replaces Google Cloud Speech-to-Text (paid) with:
- Browser Web Speech API (free, unlimited)
- Backend mock for testing
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class SpeechTool:
    """Backend speech transcription placeholder.

    Real transcription is handled in the browser via the Web Speech API
    (SpeechRecognition). This backend tool:
    1. Returns mock transcripts for testing/demo
    2. Optionally integrates with Gemini API for post-processing
    """

    def __init__(self, project_id: str = "local", location: str = "us-central1"):
        self._project_id = project_id
        self._location = location

    async def transcribe(
        self, audio_bytes: bytes, language_code: str = "en-IN"
    ) -> str | None:
        """Transcribe audio bytes to text.

        In production: audio is transcribed in the browser using Web Speech API.
        This backend mock returns sample transcripts for demo purposes.

        Args:
            audio_bytes:   Raw audio content (ignored in mock mode).
            language_code: BCP-47 language code.

        Returns:
            Transcript string, or ``None`` on failure.
        """
        # Mock transcript for demo - real transcription happens in browser
        logger.info("SpeechTool.transcribe() called (mock mode)")
        await asyncio.sleep(0.1)  # Simulate processing time
        return "There is a large pothole on MG Road near the school. Please fix it as soon as possible."
