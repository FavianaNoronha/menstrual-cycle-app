from datetime import date, datetime, timedelta, timezone

from cycle_engine import Impact, PainLog, Period

from app.config import Settings
from app.conversation import ConversationHandler
from app.main import create_app
from app.store import MemoryStore
from fastapi.testclient import TestClient

from test_whatsapp_flow import SETTINGS, FakeMessenger, onboard, post, text

WA = "919900000001"
FIRST = date(2026, 6, 1)


def _client(today):
    store, messenger = MemoryStore(), FakeMessenger()
    handler = ConversationHandler(store, messenger, today=lambda: today)
    client = TestClient(create_app(SETTINGS, handler))
    onboard(client)
    u = store.get_or_create(WA)
    for i in range(4):  # periods every 28 days, each with a bad pain day that stopped work
        start = FIRST + timedelta(days=28 * i)
        u.record.periods.append(Period(start, start + timedelta(days=4)))
        u.record.pain.append(PainLog(start, 7 + (i % 2), impacts={Impact.WORK}))
    store.save(u)
    messenger.sent.clear()
    return client, store, messenger


def _before_period():
    return FIRST + timedelta(days=28 * 3 + 26)  # 2 days before the 5th period is expected


def test_plan_command_shows_line_without_naming_a_drug():
    client, _, m = _client(_before_period())
    post(client, text("plan"))
    body = m.texts()[-2]  # the last message is the "did this help?" question
    assert "/10" in body and "pharmacist" in body.lower() and "BRIEF" in body  # repeats -> doctor line
    assert not any(w in body.lower() for w in ("ibuprofen", "mefenamic", "meftal", "paracetamol", "mg"))


def test_nudge_sent_once_per_predicted_period():
    client, _, m = _client(_before_period())
    post(client, text("hi"))
    post(client, text("hi"))
    nudges = [b for b in m.texts() if "weather forecast" in b]
    assert len(nudges) == 1


def test_no_nudge_mid_cycle():
    client, _, m = _client(FIRST + timedelta(days=28 * 3 + 12))
    post(client, text("hi"))
    assert not any("weather forecast" in b for b in m.texts())


def test_discreet_mode_toggles_and_neutralises_nudge():
    client, store, m = _client(_before_period())
    post(client, text("discreet"))
    assert store.get_or_create(WA).discreet is True
    post(client, text("hi"))
    sent = m.texts()
    assert any("note is waiting" in b for b in sent)
    assert not any("weather forecast" in b for b in sent)
    post(client, text("discreet"))
    assert store.get_or_create(WA).discreet is False


def test_new_fields_survive_sqlite_round_trip_and_old_rows(tmp_path):
    from cryptography.fernet import Fernet
    from app.store.sqlite import SqliteStore

    store = SqliteStore(str(tmp_path / "d.sqlite"), Fernet.generate_key().decode())
    u = store.get_or_create(WA)
    u.discreet, u.nudged_for = True, "2026-11-01"
    store.save(u)
    again = store.get_or_create(WA)
    assert again.discreet is True and again.nudged_for == "2026-11-01"
    import json
    old = json.loads(SqliteStore._pack(u))
    del old["discreet"], old["nudged_for"]
    assert SqliteStore._unpack(json.dumps(old).encode()).discreet is False


def test_unprompted_nudge_never_says_period_or_pain():
    from app.i18n import MESSAGES
    for key in ("nudge_intro", "nudge_discreet"):
        for lang, text in MESSAGES[key].items():
            low = text.lower()
            assert "period" not in low and "pain" not in low and "cramp" not in low, (key, lang)
