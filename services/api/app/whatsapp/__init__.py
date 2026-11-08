"""WhatsApp Business Platform (Cloud API) integration.

Policy note: since 15 Jan 2026 Meta bans general-purpose AI assistants on the
Business API. Ritu's bot must stay a scoped cycle-tracking service; anything
off-topic gets a polite refusal (see conversation handler).
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Protocol

import httpx


def verify_signature(app_secret: str, body: bytes, header: str | None) -> bool:
    """Validate X-Hub-Signature-256 (HMAC-SHA256 of the raw body with the app secret)."""
    if not app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


@dataclass
class InboundMessage:
    message_id: str
    wa_id: str
    kind: str  # "text", "audio", "button", "unsupported"
    text: str = ""
    media_id: str | None = None
    reply_id: str | None = None  # id of a tapped button / list row


def parse_webhook(payload: dict) -> list[InboundMessage]:
    out: list[InboundMessage] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                kind = msg.get("type")
                base = {"message_id": msg.get("id", ""), "wa_id": msg.get("from", "")}
                if kind == "text":
                    out.append(InboundMessage(kind="text", text=msg.get("text", {}).get("body", ""), **base))
                elif kind == "audio":
                    out.append(InboundMessage(kind="audio", media_id=msg.get("audio", {}).get("id"), **base))
                elif kind == "interactive":
                    inter = msg.get("interactive", {})
                    reply = inter.get("button_reply") or inter.get("list_reply") or {}
                    out.append(
                        InboundMessage(kind="button", reply_id=reply.get("id"), text=reply.get("title", ""), **base)
                    )
                elif kind == "button":  # quick-reply on a template
                    out.append(
                        InboundMessage(kind="button", reply_id=msg.get("button", {}).get("payload"),
                                       text=msg.get("button", {}).get("text", ""), **base)
                    )
                else:
                    out.append(InboundMessage(kind="unsupported", **base))
    return out


class Messenger(Protocol):
    def send_text(self, to: str, body: str) -> None: ...
    def send_buttons(self, to: str, body: str, buttons: list[tuple[str, str]]) -> None: ...
    def send_list(self, to: str, body: str, button: str, rows: list[tuple[str, str]]) -> None: ...
    def download_media(self, media_id: str) -> tuple[bytes, str]: ...


class CloudApiMessenger:
    """Thin client for the WhatsApp Cloud API."""

    def __init__(self, access_token: str, phone_number_id: str, api_version: str = "v21.0",
                 client: httpx.Client | None = None) -> None:
        self._token = access_token
        self._base = f"https://graph.facebook.com/{api_version}"
        self._phone_id = phone_number_id
        self._http = client or httpx.Client(timeout=15)

    def _post(self, payload: dict) -> None:
        resp = self._http.post(
            f"{self._base}/{self._phone_id}/messages",
            headers={"Authorization": f"Bearer {self._token}"},
            json={"messaging_product": "whatsapp", **payload},
        )
        resp.raise_for_status()

    def send_text(self, to: str, body: str) -> None:
        self._post({"to": to, "type": "text", "text": {"body": body[:4096]}})

    def send_buttons(self, to: str, body: str, buttons: list[tuple[str, str]]) -> None:
        """Up to 3 reply buttons; titles max 20 characters."""
        self._post({
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body[:1024]},
                "action": {"buttons": [{"type": "reply", "reply": {"id": i, "title": t[:20]}} for i, t in buttons[:3]]},
            },
        })

    def send_list(self, to: str, body: str, button: str, rows: list[tuple[str, str]]) -> None:
        """Up to 10 rows; row titles max 24 characters."""
        self._post({
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body[:1024]},
                "action": {"button": button[:20], "sections": [{"title": "Ritu", "rows": [
                    {"id": i, "title": t[:24]} for i, t in rows[:10]
                ]}]},
            },
        })

    def download_media(self, media_id: str) -> tuple[bytes, str]:
        headers = {"Authorization": f"Bearer {self._token}"}
        meta = self._http.get(f"{self._base}/{media_id}", headers=headers)
        meta.raise_for_status()
        info = meta.json()
        blob = self._http.get(info["url"], headers=headers)
        blob.raise_for_status()
        return blob.content, info.get("mime_type", "audio/ogg")
