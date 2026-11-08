import hashlib
import hmac
import json
from datetime import date

from fastapi.testclient import TestClient

from app.config import Settings
from app.conversation import ConversationHandler
from app.main import create_app
from app.store import MemoryStore
from app.whatsapp import verify_signature

SECRET = "test-secret"
SETTINGS = Settings(whatsapp_verify_token="verify-me", whatsapp_app_secret=SECRET)


class FakeMessenger:
    def __init__(self):
        self.sent = []

    def send_text(self, to, body):
        self.sent.append(("text", to, body))

    def send_buttons(self, to, body, buttons):
        self.sent.append(("buttons", to, body, buttons))

    def send_list(self, to, body, button, rows):
        self.sent.append(("list", to, body, rows))

    def download_media(self, media_id):
        return b"fake-ogg", "audio/ogg"

    def texts(self):
        return [m[2] for m in self.sent if m[0] == "text"]


class FakeTranscriber:
    def __init__(self, text, lang):
        self.text, self.lang = text, lang

    def transcribe(self, audio, mime):
        return self.text, self.lang


def make(today=date(2026, 11, 8), transcriber=None):
    store, messenger = MemoryStore(), FakeMessenger()
    handler = ConversationHandler(store, messenger, transcriber=transcriber, today=lambda: today)
    client = TestClient(create_app(SETTINGS, handler))
    return client, store, messenger


_counter = iter(range(10_000))


def payload(message: dict, wa_id="919900000001"):
    message = {"from": wa_id, "id": f"wamid.{next(_counter)}", **message}
    return {"entry": [{"changes": [{"value": {"messages": [message]}}]}]}


def post(client, body: dict):
    raw = json.dumps(body).encode()
    sig = "sha256=" + hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return client.post("/webhooks/whatsapp", content=raw,
                       headers={"x-hub-signature-256": sig, "content-type": "application/json"})


def text(body):
    return payload({"type": "text", "text": {"body": body}})


def tap(reply_id, title=""):
    return payload({"type": "interactive", "interactive": {"type": "button_reply",
                                                            "button_reply": {"id": reply_id, "title": title}}})


def onboard(client, lang="en"):
    post(client, text("hi"))
    post(client, tap(f"lang_{lang}"))
    post(client, tap("consent_yes"))


def test_signature_check():
    assert verify_signature("s", b"{}", "sha256=" + hmac.new(b"s", b"{}", hashlib.sha256).hexdigest())
    assert not verify_signature("s", b"{}", "sha256=deadbeef")
    assert not verify_signature("s", b"{}", None)


def test_verify_handshake():
    client, _, _ = make()
    ok = client.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "verify-me",
                                                   "hub.challenge": "42"})
    assert ok.status_code == 200 and ok.text == "42"
    bad = client.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "nope"})
    assert bad.status_code == 403


def test_unsigned_post_rejected():
    client, _, _ = make()
    assert client.post("/webhooks/whatsapp", json=text("hi")).status_code == 401


def test_onboarding_language_then_consent_then_welcome_in_kannada():
    client, store, messenger = make()
    post(client, text("hi"))
    assert messenger.sent[0][0] == "list"
    post(client, tap("lang_kn"))
    assert messenger.sent[1][0] == "buttons" and "ಒಪ್ಪುತ್ತೀರಾ" in messenger.sent[1][2]
    post(client, tap("consent_yes"))
    assert "ಸಿದ್ಧ" in messenger.texts()[-1]
    user = store.get_or_create("919900000001")
    assert user.language == "kn" and user.consented_at is not None


def test_nothing_stored_when_consent_declined():
    client, store, messenger = make()
    post(client, text("hi"))
    post(client, tap("lang_hi"))
    post(client, tap("consent_no"))
    assert not store.exists("919900000001")
    assert "कुछ भी सेव नहीं" in messenger.texts()[-1]


def test_log_period_and_symptoms_reads_back():
    client, store, messenger = make()
    onboard(client)
    post(client, text("period started, heavy, cramps 6/10, craving sweets"))
    reply = messenger.texts()[-1]
    assert reply.startswith("Saved:") and "period started" in reply and "pain 6/10" in reply
    rec = store.get_or_create("919900000001").record
    assert rec.periods[0].start == date(2026, 11, 8)
    assert rec.pain[0].score == 6
    assert rec.symptoms[0].craving_types == {"sweet"}


def test_pain_without_score_asks_follow_up_and_offers_help_when_severe():
    client, store, messenger = make()
    onboard(client, "hi")
    post(client, text("bahut pet dard"))
    assert "0 (बिल्कुल नहीं)" in messenger.texts()[-1]
    post(client, text("8"))
    texts = messenger.texts()
    assert "दर्द 8/10" in texts[-2] and "पीरियड के दर्द के लिए" in texts[-1]
    assert store.get_or_create("919900000001").record.pain[0].score == 8


def test_red_flag_triggers_urgent_message_once():
    client, _, messenger = make()
    onboard(client)
    post(client, text("very heavy, soaking a pad every hour, feeling dizzy"))
    urgent = [m for m in messenger.texts() if "medical care today" in m]
    assert len(urgent) == 1
    post(client, text("still heavy, every hour"))
    assert len([m for m in messenger.texts() if "medical care today" in m]) == 1


def test_off_topic_is_politely_refused():
    client, _, messenger = make()
    onboard(client)
    post(client, text("write me a poem about the ocean please"))
    assert "only help with tracking" in messenger.texts()[-1]


def test_status_and_delete():
    client, store, messenger = make()
    onboard(client)
    post(client, text("period started"))
    post(client, text("status"))
    assert "Cycle day 1" in messenger.texts()[-1]
    post(client, text("DELETE"))
    assert not store.exists("919900000001")


def test_voice_note_in_tamil_is_transcribed_and_logged():
    client, store, messenger = make(transcriber=FakeTranscriber("இன்று மாதவிடாய் வந்தது, வலி 5/10", "ta-IN"))
    onboard(client, "ta")
    post(client, payload({"type": "audio", "audio": {"id": "media-1"}}))
    assert messenger.texts()[-1].startswith("சேமிக்கப்பட்டது")
    assert store.get_or_create("919900000001").record.pain[0].score == 5


def test_duplicate_webhook_deliveries_are_processed_once():
    client, _, messenger = make()
    body = text("hi")
    post(client, body)
    post(client, body)
    assert len(messenger.sent) == 1
