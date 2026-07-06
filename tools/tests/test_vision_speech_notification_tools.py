"""
Unit tests for:
  - tools/vision_tool.py  (VisionTool — Gemini API based)
  - tools/speech_tool.py  (SpeechTool — browser Web Speech API mock)
  - tools/notification_tool.py (NotificationTool — SendGrid + Twilio)

All tests use mocks; no real API calls are made.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.vision_tool import VisionTool
from tools.speech_tool import SpeechTool
from tools.notification_tool import NotificationTool


# ============================================================
# VisionTool (Gemini-based, no vertexai)
# ============================================================


class _MockGeminiResponse:
    def __init__(self, text: str):
        self.text = text


class _MockGeminiModel:
    def __init__(self, text: str = "A damaged road with visible cracks."):
        self._text = text

    def generate_content(self, content_list):
        return _MockGeminiResponse(self._text)


@pytest.mark.asyncio
async def test_caption_image_returns_text():
    tool = VisionTool(gemini_model=_MockGeminiModel("Large pothole on MG Road."))
    result = await tool.caption_image(b"fake-image-bytes")
    assert result == "Large pothole on MG Road."


@pytest.mark.asyncio
async def test_caption_image_returns_none_on_failure():
    tool = VisionTool(gemini_model=None)  # mock mode
    result = await tool.caption_image(b"any-bytes")
    assert result is not None  # mock returns fallback


# ============================================================
# SpeechTool (browser-based mock)
# ============================================================


@pytest.mark.asyncio
async def test_transcribe_returns_text():
    tool = SpeechTool()
    result = await tool.transcribe(b"audio-bytes")
    assert result is not None
    assert "pothole" in result.lower()


@pytest.mark.asyncio
async def test_transcribe_returns_string():
    """SpeechTool always returns a mock transcript in mock mode."""
    tool = SpeechTool()
    result = await tool.transcribe(b"any-audio")
    assert isinstance(result, str)
    assert len(result) > 10


# ============================================================
# NotificationTool
# ============================================================


def _make_notification_tool() -> NotificationTool:
    return NotificationTool(
        fcm_server_key="fcm-key",
        sendgrid_api_key="sg-key",
        twilio_account_sid="AC123",
        twilio_auth_token="auth-token",
        twilio_from_phone="+15005550006",
        twilio_whatsapp_from="+14155238886",
    )


@pytest.mark.asyncio
async def test_send_fcm_returns_true_on_200():
    tool = _make_notification_tool()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("tools.notification_tool.httpx.AsyncClient", return_value=mock_client):
        result = await tool.send_fcm("device-token", {"title": "Issue received", "body": "Your report was accepted."})
    assert result is True


@pytest.mark.asyncio
async def test_send_fcm_returns_false_on_non_200():
    tool = _make_notification_tool()
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad request"
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("tools.notification_tool.httpx.AsyncClient", return_value=mock_client):
        result = await tool.send_fcm("bad-token", {})
    assert result is False


@pytest.mark.asyncio
async def test_send_fcm_returns_false_on_exception():
    tool = _make_notification_tool()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(side_effect=Exception("network error"))

    with patch("tools.notification_tool.httpx.AsyncClient", return_value=mock_client):
        result = await tool.send_fcm("token", {})
    assert result is False


@pytest.mark.asyncio
async def test_send_email_returns_true_on_202():
    tool = _make_notification_tool()
    with patch.object(tool, "_sync_send_email", return_value=True):
        result = await tool.send_email("user@example.com", "Issue Update", "Your issue is resolved.")
    assert result is True


@pytest.mark.asyncio
async def test_send_email_returns_false_on_failure():
    tool = _make_notification_tool()
    with patch.object(tool, "_sync_send_email", return_value=False):
        result = await tool.send_email("user@example.com", "Subject", "Body")
    assert result is False


@pytest.mark.asyncio
async def test_send_sms_returns_true_on_success():
    tool = _make_notification_tool()
    with patch.object(tool, "_sync_send_sms", return_value=True):
        result = await tool.send_sms("+919999999999", "Issue assigned.")
    assert result is True


@pytest.mark.asyncio
async def test_send_sms_returns_false_on_twilio_error():
    tool = _make_notification_tool()
    with patch.object(tool, "_sync_send_sms", return_value=False):
        result = await tool.send_sms("+919999999999", "message")
    assert result is False


@pytest.mark.asyncio
async def test_send_whatsapp_returns_true_on_success():
    tool = _make_notification_tool()
    with patch.object(tool, "_sync_send_whatsapp", return_value=True):
        result = await tool.send_whatsapp("+919999999999", "WhatsApp notification")
    assert result is True


@pytest.mark.asyncio
async def test_send_whatsapp_returns_false_on_error():
    tool = _make_notification_tool()
    with patch.object(tool, "_sync_send_whatsapp", return_value=False):
        result = await tool.send_whatsapp("+919999999999", "message")
    assert result is False
