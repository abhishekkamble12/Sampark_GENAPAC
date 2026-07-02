"""
tools/notification_tool.py — Multi-channel notification tool for the Sampark AI Platform.

Supports FCM (push), email (SendGrid), SMS (Twilio), and WhatsApp (Twilio).
All methods return True on success and False on failure — they never raise.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_FCM_URL = "https://fcm.googleapis.com/fcm/send"
_TIMEOUT = 10.0


class NotificationTool:
    """Multi-channel notification dispatcher.

    Args:
        fcm_server_key:        Firebase Cloud Messaging server key.
        sendgrid_api_key:      SendGrid API key.
        twilio_account_sid:    Twilio Account SID.
        twilio_auth_token:     Twilio Auth Token.
        twilio_from_phone:     Twilio SMS sender phone number (E.164 format).
        twilio_whatsapp_from:  Twilio WhatsApp sender number (E.164, without prefix).
        sendgrid_from_email:   Sender email address for SendGrid.
    """

    def __init__(
        self,
        fcm_server_key: str,
        sendgrid_api_key: str,
        twilio_account_sid: str,
        twilio_auth_token: str,
        twilio_from_phone: str,
        twilio_whatsapp_from: str,
        sendgrid_from_email: str = "noreply@sampark.gov.in",
    ) -> None:
        self._fcm_server_key = fcm_server_key
        self._sendgrid_api_key = sendgrid_api_key
        self._twilio_account_sid = twilio_account_sid
        self._twilio_auth_token = twilio_auth_token
        self._twilio_from_phone = twilio_from_phone
        self._twilio_whatsapp_from = twilio_whatsapp_from
        self._sendgrid_from_email = sendgrid_from_email

    # ------------------------------------------------------------------
    # FCM (Firebase Cloud Messaging)
    # ------------------------------------------------------------------

    async def send_fcm(self, token: str, message: dict[str, Any]) -> bool:
        """Send a Firebase Cloud Messaging push notification.

        Args:
            token:   FCM device registration token.
            message: Notification payload dict ``{title, body}``.

        Returns:
            ``True`` on HTTP 200, ``False`` on any error.
        """
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    _FCM_URL,
                    headers={
                        "Authorization": f"key={self._fcm_server_key}",
                        "Content-Type": "application/json",
                    },
                    json={"to": token, "notification": message},
                )
            if resp.status_code == 200:
                return True
            logger.warning("FCM returned status %d: %s", resp.status_code, resp.text)
            return False
        except Exception:
            logger.exception("send_fcm failed for token=%s", token[:8] + "...")
            return False

    # ------------------------------------------------------------------
    # Email (SendGrid)
    # ------------------------------------------------------------------

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send a transactional email via SendGrid.

        Args:
            to:      Recipient email address.
            subject: Email subject line.
            body:    Plain-text email body.

        Returns:
            ``True`` on HTTP 200/202, ``False`` on any error.
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None, self._sync_send_email, to, subject, body
            )
        except Exception:
            logger.exception("send_email failed for to=%s", to)
            return False

    def _sync_send_email(self, to: str, subject: str, body: str) -> bool:
        try:
            from sendgrid import SendGridAPIClient  # type: ignore[import-untyped]
            from sendgrid.helpers.mail import Mail  # type: ignore[import-untyped]

            message = Mail(
                from_email=self._sendgrid_from_email,
                to_emails=to,
                subject=subject,
                plain_text_content=body,
            )
            sg = SendGridAPIClient(self._sendgrid_api_key)
            response = sg.send(message)
            if response.status_code in (200, 202):
                return True
            logger.warning("SendGrid returned status %d", response.status_code)
            return False
        except Exception:
            logger.exception("SendGrid send_email failed for to=%s", to)
            return False

    # ------------------------------------------------------------------
    # SMS (Twilio)
    # ------------------------------------------------------------------

    async def send_sms(self, phone: str, message: str) -> bool:
        """Send an SMS via Twilio.

        Args:
            phone:   Recipient phone number in E.164 format (e.g. ``+919999999999``).
            message: SMS body text.

        Returns:
            ``True`` on success, ``False`` on any error.
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None, self._sync_send_sms, phone, message
            )
        except Exception:
            logger.exception("send_sms failed for phone=%s", phone)
            return False

    def _sync_send_sms(self, phone: str, message: str) -> bool:
        try:
            from twilio.rest import Client  # type: ignore[import-untyped]

            client = Client(self._twilio_account_sid, self._twilio_auth_token)
            msg = client.messages.create(
                from_=self._twilio_from_phone,
                to=phone,
                body=message,
            )
            return msg.sid is not None
        except Exception:
            logger.exception("Twilio SMS failed for phone=%s", phone)
            return False

    # ------------------------------------------------------------------
    # WhatsApp (Twilio)
    # ------------------------------------------------------------------

    async def send_whatsapp(self, phone: str, message: str) -> bool:
        """Send a WhatsApp message via Twilio.

        Args:
            phone:   Recipient phone number in E.164 format.
            message: Message body text.

        Returns:
            ``True`` on success, ``False`` on any error.
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None, self._sync_send_whatsapp, phone, message
            )
        except Exception:
            logger.exception("send_whatsapp failed for phone=%s", phone)
            return False

    def _sync_send_whatsapp(self, phone: str, message: str) -> bool:
        try:
            from twilio.rest import Client  # type: ignore[import-untyped]

            client = Client(self._twilio_account_sid, self._twilio_auth_token)
            msg = client.messages.create(
                from_=f"whatsapp:{self._twilio_whatsapp_from}",
                to=f"whatsapp:{phone}",
                body=message,
            )
            return msg.sid is not None
        except Exception:
            logger.exception("Twilio WhatsApp failed for phone=%s", phone)
            return False
