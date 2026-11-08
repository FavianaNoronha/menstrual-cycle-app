import sqlite3
from datetime import date, datetime, timezone

import pytest
from cryptography.fernet import Fernet
from cycle_engine import PainLog, Period

from app.config import Settings
from app.conversation import ConversationHandler
from app.main import create_app
from app.store.sqlite import SqliteStore

from test_whatsapp_flow import FakeMessenger, onboard, post, text

KEY = Fernet.generate_key().decode()


def test_user_round_trips_across_restart(tmp_path):
    path = str(tmp_path / "db.sqlite")
    store = SqliteStore(path, KEY)
    u = store.get_or_create("919900000001")
    u.language, u.consented_at = "kn", datetime(2026, 11, 9, 1, 2, tzinfo=timezone.utc)
    u.record.periods.append(Period(date(2026, 11, 1), date(2026, 11, 5)))
    u.record.pain.append(PainLog(date(2026, 11, 2), 7, duration_minutes=90))
    u.pending["pain"] = {"locations": ["lower_back"]}
    u.alerted_codes.add("pain_with_fainting")
    store.save(u)
    store.close()

    again = SqliteStore(path, KEY).get_or_create("919900000001")
    assert again.language == "kn" and again.consented_at == u.consented_at
    assert again.record == u.record and again.pending == u.pending and again.alerted_codes == {"pain_with_fainting"}


def test_nothing_readable_on_disk(tmp_path):
    path = str(tmp_path / "db.sqlite")
    store = SqliteStore(path, KEY)
    u = store.get_or_create("919900000001")
    u.record.pain.append(PainLog(date(2026, 11, 2), 9))
    store.save(u)
    store.close()
    raw = open(path, "rb").read()
    assert b"919900000001" not in raw and b"lower_abdomen" not in raw and b"score" not in raw
    rows = sqlite3.connect(path).execute("SELECT id FROM users").fetchall()
    assert len(rows) == 1 and "919900000001" not in rows[0][0]


def test_delete_removes_everything(tmp_path):
    store = SqliteStore(str(tmp_path / "db.sqlite"), KEY)
    store.save(store.get_or_create("919900000001"))
    assert store.exists("919900000001")
    store.delete("919900000001")
    assert not store.exists("919900000001")
    assert store.get_or_create("919900000001").language is None


def test_wrong_key_is_refused_not_silently_reset(tmp_path):
    path = str(tmp_path / "db.sqlite")
    s1 = SqliteStore(path, KEY)
    s1.save(s1.get_or_create("919900000001"))
    s1.close()
    with pytest.raises(RuntimeError, match="does not match"):
        SqliteStore(path, Fernet.generate_key().decode())


def test_key_is_required():
    with pytest.raises(ValueError):
        SqliteStore(":memory:", "")


def test_message_dedupe_persists(tmp_path):
    path = str(tmp_path / "db.sqlite")
    a = SqliteStore(path, KEY)
    assert a.seen_message("wamid.1") is False
    assert a.seen_message("wamid.1") is True
    a.close()
    assert SqliteStore(path, KEY).seen_message("wamid.1") is True


def test_whole_bot_flow_survives_a_restart(tmp_path):
    from fastapi.testclient import TestClient

    from test_whatsapp_flow import SECRET

    path = str(tmp_path / "db.sqlite")
    settings = Settings(whatsapp_verify_token="v", whatsapp_app_secret=SECRET)

    def boot():
        messenger = FakeMessenger()
        handler = ConversationHandler(SqliteStore(path, KEY), messenger, today=lambda: date(2026, 11, 8))
        return TestClient(create_app(settings, handler)), messenger

    c1, _ = boot()
    onboard(c1)
    post(c1, text("cramps 8/10, missed work"))
    c2, m2 = boot()  # "server restarted"
    post(c2, text("status"))  # no re-onboarding needed
    assert m2.sent and "consent" not in m2.sent[-1][2].lower()
    post(c2, text("delete"))
    c3, _ = boot()
    assert not SqliteStore(path, KEY).exists("919900000001")
