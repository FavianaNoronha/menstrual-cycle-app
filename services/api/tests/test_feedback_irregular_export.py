import csv
import io
from datetime import date, timedelta

from cycle_engine import PainLog, Period, export_csv, is_irregular, predict_next_period
from cycle_engine.models import CycleRecord

from app.conversation import ConversationHandler
from app.main import create_app
from app.store import MemoryStore
from fastapi.testclient import TestClient

from test_whatsapp_flow import SETTINGS, FakeMessenger, onboard, post, text

WA = "919900000001"
FIRST = date(2026, 1, 1)


def _client(lengths, today=None):
    store, messenger = MemoryStore(), FakeMessenger()
    start = FIRST
    today = today or FIRST + timedelta(days=sum(lengths) + 10)
    handler = ConversationHandler(store, messenger, today=lambda: today)
    client = TestClient(create_app(SETTINGS, handler))
    onboard(client)
    u = store.get_or_create(WA)
    u.record.periods.append(Period(start, start + timedelta(days=4)))
    for n in lengths:
        start += timedelta(days=n)
        u.record.periods.append(Period(start, start + timedelta(days=4)))
    store.save(u)
    messenger.sent.clear()
    return client, store, messenger


def _record(lengths):
    r, d = CycleRecord(), FIRST
    r.periods.append(Period(d))
    for n in lengths:
        d += timedelta(days=n)
        r.periods.append(Period(d))
    return r


# ---- irregular mode -------------------------------------------------------------
def test_regular_cycles_not_irregular_and_narrow():
    r = _record([28, 29, 28, 27, 28, 28])
    p = predict_next_period(r)
    assert not p.irregular and (p.latest - p.earliest).days <= 6


def test_wide_spread_is_irregular_and_range_covers_every_observed_length():
    lengths = [24, 45, 31, 52]
    assert is_irregular(lengths)
    r = _record(lengths)
    p = predict_next_period(r)
    last = r.last_period().start
    assert p.irregular and p.confidence.value == "low" and p.basis == "irregular_full_range"
    assert p.earliest <= last + timedelta(days=24) and p.latest >= last + timedelta(days=52)


def test_two_cycles_are_never_called_irregular():
    assert not is_irregular([20, 60])


def test_wrong_button_widens_range_and_is_capped():
    r = _record([28, 28, 29, 28, 28])
    base = predict_next_period(r)
    r.prediction_misses = 1
    one = predict_next_period(r)
    r.prediction_misses = 50
    many = predict_next_period(r)
    width = lambda p: (p.latest - p.earliest).days  # noqa: E731
    assert width(one) == width(base) + 4
    assert width(many) == width(base) + 12  # capped at 3 presses
    assert one.confidence.value == "low"


def test_status_for_irregular_user_explains_wide_range_and_mentions_doctor():
    client, _, m = _client([24, 45, 31, 52])
    post(client, text("when is my next period"))
    body = m.texts()[-1]
    assert "wide range" in body and "doctor" in body and "WRONG" in body


def test_wrong_command_widens_stores_feedback_and_survives_delete():
    client, store, m = _client([28, 28, 29, 28])
    post(client, text("when is my next period"))
    before = m.texts()[-1]
    post(client, text("WRONG"))
    u = store.get_or_create(WA)
    assert u.record.prediction_misses == 1
    assert u.feedback[-1] == {"kind": "prediction", "answer": "wrong", "day": u.feedback[-1]["day"]}
    assert "widened" in m.texts()[-1] and m.texts()[-1] != before
    post(client, text("DELETE"))
    assert not store.exists(WA)


# ---- export -----------------------------------------------------------------------
def test_export_csv_has_everything_she_logged_and_opens_as_csv():
    r = _record([28, 28])
    r.pain.append(PainLog(FIRST, 7))
    rows = list(csv.reader(io.StringIO(export_csv(r))))
    assert rows[0] == ["type", "date", "value", "notes"]
    assert sum(1 for x in rows if x[0] == "period_start") == 3
    assert ["pain", FIRST.isoformat(), "7", ""] in rows


def test_export_command_sends_header_csv_and_footer():
    client, _, m = _client([28, 28, 28])
    post(client, text("EXPORT"))
    sent = m.texts()
    assert "free" in sent[0] and "period_start" in "\n".join(sent) and "DELETE" in sent[-1]


def test_export_splits_long_data_under_whatsapp_limit():
    client, store, m = _client([28])
    u = store.get_or_create(WA)
    d = FIRST
    for i in range(400):
        u.record.pain.append(PainLog(d + timedelta(days=i), 5))
    store.save(u)
    post(client, text("EXPORT"))
    assert all(len(x) < 4096 for x in m.texts()) and len(m.texts()) >= 4


# ---- "did this help?" ---------------------------------------------------------------
def test_plan_asks_if_it_helped_and_records_answer():
    client, store, m = _client([28, 28, 28])
    post(client, text("PLAN"))
    assert "Did this help" in m.texts()[-1]
    post(client, text("1"))
    assert store.get_or_create(WA).feedback[-1]["kind"] == "plan"
    assert store.get_or_create(WA).feedback[-1]["answer"] == "yes"
    assert "helped" not in store.get_or_create(WA).pending


def test_no_answer_asks_why_and_stores_reason():
    client, store, m = _client([28, 28, 28])
    post(client, text("BRIEF"))
    post(client, text("3"))
    assert "what would have helped" in m.texts()[-1]
    post(client, text("too long and too many words"))
    f = store.get_or_create(WA).feedback[-1]
    assert f["kind"] == "brief" and f["answer"] == "no" and f["why"].startswith("too long")


def test_ignoring_the_question_does_not_swallow_the_next_message():
    client, store, m = _client([28, 28, 28])
    post(client, text("PLAN"))
    post(client, text("period started today"))
    assert "period started" in m.texts()[-1] or "Saved" in m.texts()[-1] or "Logged" in m.texts()[-1]
    assert store.get_or_create(WA).feedback == []


def test_digit_is_a_pain_score_when_pain_is_pending_not_feedback():
    client, store, m = _client([28, 28, 28])
    post(client, text("PLAN"))
    u = store.get_or_create(WA)
    u.pending["pain"] = {"locations": [], "fever": False, "fainted_or_dizzy": False}
    store.save(u)
    post(client, text("2"))
    assert store.get_or_create(WA).feedback == []
    assert store.get_or_create(WA).record.pain[-1].score == 2


def test_feedback_counts_have_no_ids_or_text():
    client, store, _ = _client([28, 28, 28])
    post(client, text("PLAN"))
    post(client, text("3"))
    post(client, text("bad"))
    counts = store.feedback_counts()
    assert counts == {"plan": {"no": 1}}


def test_promise_command():
    client, _, m = _client([28, 28, 28])
    post(client, text("PROMISE"))
    assert "free, forever" in m.texts()[-1] and "EXPORT" in m.texts()[-1]


def test_late_period_gets_neutral_calm_reply_with_test_and_emergency_advice():
    client, _, m = _client([28, 28, 28])
    post(client, text("my period is late"))
    body = "\n".join(m.texts()).lower()
    assert "very common" in body and "urine test" in body and "hospital now" in body
    assert not any(w in body for w in ("unmarried", "single", "sex", "sin", "shame", "careless"))


def test_late_phrases_in_other_languages_and_started_still_logs():
    from app.nlu import RuleExtractor

    ex = RuleExtractor()
    for phrase in ["period nahi aaya", "पीरियड नहीं आया", "పీరియడ్ రాలేదు", "பீரியட் வரவில்லை", "mc late"]:
        assert ex.extract(phrase).intent == "late", phrase
    assert ex.extract("period started today").period_started
