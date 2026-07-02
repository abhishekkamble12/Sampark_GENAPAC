"""
Unit tests for:
  - tools/vision_tool.py  (VisionTool)
  - tools/speech_tool.py  (SpeechTool)
  - tools/notification_tool.py (NotificationTool)

All Google Cloud / Twilio / SendGrid SDK calls are mocked.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.vision_tool import VisionTool
from tools.speech_tool import SpeechTool
from tools.notification_tool import NotificationTool


# ============================================================
# VisionTool
# ============================================================


@pytest.mark.asyncio
async def test_caption_image_returns_text():
    tool = VisionTool(project_id="proj", location="us-central1")
    mock_response = MagicMock()
    mock_response.text = "  Large pothole on MG Road.  "

    with patch.object(tool, "_sync_caption_image", return_value="Large pothole on MG Road."):
        result = await tool.caption_image(b"fake-image-bytes")

    assert result == "Large pothole on MG Road."


@pytest.mark.asyncio
async def test_caption_image_returns_none_on_failure():
    tool = VisionTool(project_id="proj")
    with patch.object(tool, "_sync_caption_image", side_effect=Exception("API error")):
        result = await tool.caption_image(b"bad-bytes")
    assert result is None


@pytest.mark.asyncio
async def test_caption_image_returns_none_when_empty_text():
    tool = VisionTool(project_id="proj")
    with patch.object(tool, "_sync_caption_image", return_value=None):
        result = await tool.caption_image(b"blank-image")
    assert result is None


def test_sync_caption_image_returns_none_when_no_vertexai(monkeypatch):
    """If vertexai import fails, _sync_caption_image returns None."""
    tool = VisionTool(project_id="proj")
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "vertexai":
            raise ImportError("vertexai not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    result = tool._sync_caption_image(b"bytes")
    assert result is None


# ============================================================
# SpeechTool
# ============================================================


@pytest.mark.asyncio
async def test_transcribe_returns_text():
    tool = SpeechTool(project_id="proj")
    with patch.object(tool, "_sync_transcribe", return_value="There is a broken road near school"):
        result = await tool.transcribe(b"audio-bytes")
    assert result == "There is a broken road near school"


@pytest.mark.asyncio
async def test_transcribe_returns_none_on_failure():
    tool = SpeechTool(project_id="proj")
    with patch.object(tool, "_sync_transcribe", side_effect=Exception("Speech API error")):
        result = await tool.transcribe(b"bad-audio")
    assert result is None


@pytest.mark.asyncio
async def test_transcribe_returns_none_when_empty_transcript():
    tool = SpeechTool(project_id="proj")
    with patch.object(tool, "_sync_transcribe", return_value=None):
        result = await tool.transcribe(b"silence")
    assert result is None


def test_sync_transcribe_returns_none_when_no_sdk(monkeypatch):
    """If google.cloud.speech_v2 import fails, _sync_transcribe returns None."""
    tool = SpeechTool(project_id="proj")
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if "speech_v2" in name:
            raise ImportError("speech_v2 not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    result = tool._sync_transcribe(b"audio", "en-IN")
    assert result is None


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
        result = await tool.send_sms("+919999999999", "Your issue has been assigned.")
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


def test_sync_send_email_returns_false_when_sendgrid_missing(monkeypatch):
    """If sendgrid is not installed, _sync_send_email returns False."""
    tool = _make_notification_tool()
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if "sendgrid" in name:
            raise ImportError("sendgrid not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    result = tool._sync_send_email("to@example.com", "subj", "body")
    assert result is False


def test_sync_send_sms_returns_false_when_twilio_missing(monkeypatch):
    """If twilio is not installed, _sync_send_sms returns False."""
    tool = _make_notification_tool()
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if "twilio" in name:
            raise ImportError("twilio not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    result = tool._sync_send_sms("+919999999999", "sms body")
    assert result is False
