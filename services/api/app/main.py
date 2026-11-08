"""FastAPI app: health check + WhatsApp webhook.

Run locally:  uvicorn app.main:app --reload --port 8000
Expose to Meta with a tunnel (e.g. ngrok) and set the callback URL to
https://<tunnel>/webhooks/whatsapp in the Meta developer console.
"""

from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from .config import Settings
from .conversation import ConversationHandler
from .speech import SarvamTranscriber
from .store import MemoryStore
from .whatsapp import CloudApiMessenger, parse_webhook, verify_signature


def create_app(settings: Settings | None = None, handler: ConversationHandler | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    if handler is None:
        handler = ConversationHandler(
            store=MemoryStore(),
            messenger=CloudApiMessenger(
                settings.whatsapp_access_token, settings.whatsapp_phone_number_id, settings.graph_api_version
            ),
            transcriber=SarvamTranscriber(settings.sarvam_api_key, settings.sarvam_stt_model)
            if settings.sarvam_api_key
            else None,
        )

    app = FastAPI(title="Cycle Companion API", version="0.1.0")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/webhooks/whatsapp", response_class=PlainTextResponse)
    def verify(request: Request) -> str:
        params = request.query_params
        if (
            params.get("hub.mode") == "subscribe"
            and settings.whatsapp_verify_token
            and params.get("hub.verify_token") == settings.whatsapp_verify_token
        ):
            return params.get("hub.challenge", "")
        raise HTTPException(status_code=403, detail="verification failed")

    @app.post("/webhooks/whatsapp")
    async def receive(request: Request, background: BackgroundTasks) -> dict:
        body = await request.body()
        if not verify_signature(settings.whatsapp_app_secret, body, request.headers.get("x-hub-signature-256")):
            raise HTTPException(status_code=401, detail="bad signature")
        for msg in parse_webhook(await request.json()):
            background.add_task(handler.handle, msg)  # reply fast; Meta retries slow webhooks
        return {"received": True}

    return app


app = create_app()
