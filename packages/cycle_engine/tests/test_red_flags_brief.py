from datetime import date, timedelta

from helpers import record_from_lengths

from cycle_engine import (
    CycleRecord,
    FlowLog,
    Period,
    Product,
    ProductUse,
    Profile,
    Saturation,
    Severity,
    build_brief,
    evaluate,
    render_text,
)
from cycle_engine.perimenopause import transition_hints


def test_soaking_hourly_is_urgent_and_sorted_first():
    rec = record_from_lengths([45, 30, 50, 29])
    rec.soaking_hourly_hours = 3
    findings = evaluate(rec, rec.last_period().start)
    assert findings[0].code == "soaking_hourly"
    assert findings[0].severity is Severity.URGENT


def test_no_period_for_90_days():
    rec = record_from_lengths([28, 28])
    today = rec.last_period().start + timedelta(days=95)
    assert "no_period_90_days" in {f.code for f in evaluate(rec, today)}


def test_no_90_day_flag_when_pregnancy_confirmed():
    rec = record_from_lengths([28, 28])
    rec.profile.positive_pregnancy_test = True
    today = rec.last_period().start + timedelta(days=95)
    assert "no_period_90_days" not in {f.code for f in evaluate(rec, today)}


def test_bleeding_after_a_year_without_periods():
    rec = CycleRecord(
        periods=[Period(date(2025, 1, 1), date(2025, 1, 4)), Period(date(2026, 3, 1), date(2026, 3, 2))],
        profile=Profile(age=51),
    )
    assert "bleeding_after_menopause" in {f.code for f in evaluate(rec, date(2026, 3, 2))}


def test_heavy_pattern_across_two_periods():
    rec = record_from_lengths([28, 28])
    full = ProductUse(Product.PAD, Saturation.FULL)
    for p in rec.sorted_periods()[1:]:
        for i in range(2):
            rec.flow.append(FlowLog(p.start + timedelta(days=i), [full, full, full]))
    assert "heavy_bleeding_pattern" in {f.code for f in evaluate(rec, date(2026, 3, 1))}


def test_transition_hints_only_from_age_35():
    lengths = [28, 36, 27, 40, 26]
    older = record_from_lengths(lengths, age=44)
    younger = record_from_lengths(lengths, age=25)
    today = older.last_period().start + timedelta(days=10)
    assert "transition_early_signs" in {f.code for f in transition_hints(older, today)}
    assert transition_hints(younger, today) == []


def test_brief_contains_questions_for_findings():
    rec = record_from_lengths([26, 41, 33, 52, 29, 45], age=30)
    brief = build_brief(rec, date(2026, 12, 1))
    assert brief["cycles_logged"] == 6
    assert any("vary a lot" in q for q in brief["questions_to_ask"])
    text = render_text(brief)
    assert "CYCLE SUMMARY" in text and "Questions to ask" in text
