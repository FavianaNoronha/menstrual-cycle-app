from datetime import timedelta

from helpers import record_from_lengths

from cycle_engine import (
    Impact,
    PainLocation,
    PainLog,
    SleepLog,
    Treatment,
    build_brief,
    pain_findings,
    render_text,
    treatment_response,
)
from cycle_engine.pain import pain_summary


def _pain_in_each_period(rec, scores, **kw):
    for p, score in zip(rec.sorted_periods(), scores):
        rec.pain.append(PainLog(p.start, score, {PainLocation.LOWER_ABDOMEN}, **kw))


def test_pain_log_validates_new_fields():
    import pytest

    from datetime import date

    with pytest.raises(ValueError):
        PainLog(date(2026, 1, 1), 5, duration_minutes=-1)
    with pytest.raises(ValueError):
        SleepLog(date(2026, 1, 1), 30)


def test_summary_counts_timing_duration_nausea_and_impact():
    rec = record_from_lengths([28, 28, 28])
    p = rec.sorted_periods()[1]
    rec.pain += [
        PainLog(p.start - timedelta(days=2), 5, duration_minutes=90),
        PainLog(p.start, 8, duration_minutes=240, nausea_vomiting=True, impacts={Impact.WORK, Impact.SLEEP}),
        PainLog(p.end + timedelta(days=10), 4),
    ]
    s = pain_summary(rec)
    assert s["pain_days_by_timing"] == {"before": 1, "during": 1, "outside": 1}
    assert s["typical_duration_minutes"] == 240
    assert s["nausea_or_vomiting_rate"] == 0.33
    assert s["days_activity_missed"] == {"work": 1, "sleep": 1}


def test_missed_activity_in_two_cycles_is_flagged_for_the_doctor():
    rec = record_from_lengths([28, 28, 28])
    _pain_in_each_period(rec, [7, 7], impacts={Impact.WORK})
    codes = {f.code for f in pain_findings(rec, rec.last_period().end)}
    assert "pain_disrupting_daily_life" in codes
    rec2 = record_from_lengths([28, 28, 28])
    _pain_in_each_period(rec2, [7, 7])
    assert "pain_disrupting_daily_life" not in {f.code for f in pain_findings(rec2, rec2.last_period().end)}


def test_treatment_response_compares_before_and_after_without_claiming_cause():
    rec = record_from_lengths([28, 28, 28, 28, 28])
    periods = rec.sorted_periods()
    _pain_in_each_period(rec, [8, 8, 4, 4, 3, 3])
    t = Treatment("Medicine from my gynaecologist", periods[2].start - timedelta(days=5), clinician_recommended=True)
    r = treatment_response(rec, t)
    assert r["status"] == "ok"
    assert r["average_peak_before"] == 8.0 and r["average_peak_after"] == 3.5
    assert "does not show the treatment caused" in r["note"]


def test_treatment_response_needs_enough_cycles():
    rec = record_from_lengths([28, 28, 28])
    _pain_in_each_period(rec, [8, 5, 4])
    t = Treatment("Heat patches", rec.sorted_periods()[1].start)
    assert treatment_response(rec, t)["status"] == "not_enough_cycles"


def test_sleep_comparison_needs_enough_data_then_reports():
    rec = record_from_lengths([28, 28, 28])
    start = rec.periods[0].start
    for i in range(6):
        rec.sleep.append(SleepLog(start + timedelta(days=i), 5.0 if i < 3 else 8.0))
        if i < 3:
            rec.pain.append(PainLog(start + timedelta(days=i), 7))
    s = pain_summary(rec)["sleep_on_high_pain_days"]
    assert s == {"high_pain_days_avg_hours": 5.0, "other_days_avg_hours": 8.0}


def test_brief_text_includes_new_pain_lines():
    rec = record_from_lengths([28, 28, 28])
    _pain_in_each_period(rec, [8, 8], duration_minutes=180, nausea_vomiting=True, impacts={Impact.WORK})
    text = render_text(build_brief(rec, rec.last_period().end))
    assert "Typical pain duration: 180 minutes" in text
    assert "Nausea or vomiting" in text and "work (2 days)" in text
    assert "stops me from working" in text  # the doctor question for pain_disrupting_daily_life
