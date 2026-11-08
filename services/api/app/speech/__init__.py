"""Speech-to-text for voice notes via Sarvam AI (Indian languages, code-mixed speech).

WhatsApp voice notes arrive as OGG/Opus. If the API rejects the format,
convert to 16 kHz mono WAV with ffmpeg before sending (Sarvam recommends 16 kHz).
The REST endpoint accepts clips up to 30 seconds; longer notes need the batch API.
"""

from __future__ import annotations

from typing import Protocol

import httpx

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"


class Transcriber(Protocol):
    def transcribe(self, audio: bytes, mime_type: str) -> tuple[str, str | None]:
        """Return (transcript, detected BCP-47 language code)."""
        ...


class SarvamTranscriber:
    def __init__(self, api_key: str, model: str = "saaras:v3", client: httpx.Client | None = None) -> None:
        self._key = api_key
        self._model = model
        self._http = client or httpx.Client(timeout=30)

    def transcribe(self, audio: bytes, mime_type: str) -> tuple[str, str | None]:
        resp = self._http.post(
            SARVAM_STT_URL,
            headers={"api-subscription-key": self._key},
            data={"model": self._model, "language_code": "unknown", "mode": "codemix"},
            files={"file": ("voice-note", audio, mime_type)},
        )
        resp.raise_for_status()
        body = resp.json()
        return body.get("transcript", ""), body.get("language_code")


BCP47_TO_APP = {"hi-IN": "hi", "kn-IN": "kn", "te-IN": "te", "ta-IN": "ta", "en-IN": "en"}
