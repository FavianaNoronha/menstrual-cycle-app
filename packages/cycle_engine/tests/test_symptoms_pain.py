from datetime import date, timedelta

from helpers import record_from_lengths

from ritu_engine import (
    PainLocation,
    PainLog,
    Severity,
    SymptomLog,
    analyze_cyclicity,
    pain_findings,
    relief_plan,
    top_cravings,
)


def _with_premenstrual_cravings(rec, cycles=2):
    """Cravings 5/6 in the week before each period, 1-2 on cycle days 4-10."""
    periods = rec.sorted_periods()
    for current, nxt in list(zip(periods, periods[1:]))[:cycles]:
        for cd in range(4, 11):
            rec.symptoms.append(SymptomLog(current.start + timedelta(days=cd - 1), {"cravings": 1, "mood_low": 2}))
        for back in range(1, 8):
            rec.symptoms.append(
                SymptomLog(nxt.start - timedelta(days=back), {"cravings": 5, "mood_low": 2}, {"sweet", "salty"})
            )
    return rec


def test_cyclical_cravings_detected_and_flat_mood_not():
    rec = _with_premenstrual_cravings(record_from_lengths([28, 28, 28]))
    patterns = {p.item: p for p in analyze_cyclicity(rec, ["cravings", "mood_low"])}
    assert patterns["cravings"].consistent
    assert patterns["cravings"].cycles_cyclical == 2
    assert not patterns["mood_low"].consistent


def test_one_cycle_is_not_enough_to_call_a_pattern():
    rec = _with_premenstrual_cravings(record_from_lengths([28, 28]), cycles=1)
    patterns = {p.item: p for p in analyze_cyclicity(rec, ["cravings"])}
    assert patterns["cravings"].cycles_cyclical == 1
    assert not patterns["cravings"].consistent


def test_top_cravings_counts_premenstrual_types():
    rec = _with_premenstrual_cravings(record_from_lengths([28, 28, 28]))
    counts = top_cravings(rec)
    assert counts["sweet"] == 14 and counts["salty"] == 14


def test_fainting_with_pain_is_urgent():
    rec = record_from_lengths([28, 28])
    today = rec.last_period().start
    rec.pain.append(PainLog(today, 7, fainted_or_dizzy=True))
    assert any(f.code == "pain_with_fainting" and f.severity is Severity.URGENT for f in pain_findings(rec, today))


def test_one_sided_pain_with_possible_pregnancy_is_urgent():
    rec = record_from_lengths([28])
    rec.profile.positive_pregnancy_test = True
    today = date(2026, 3, 1)
    rec.pain.append(PainLog(today, 6, {PainLocation.ONE_SIDE}))
    assert "one_sided_pain_pregnancy_possible" in {f.code for f in pain_findings(rec, today)}


def test_painkillers_failing_across_three_cycles_is_soon():
    rec = record_from_lengths([28, 28, 28])
    for p in rec.sorted_periods()[:3]:
        rec.pain.append(PainLog(p.start, 7, {PainLocation.LOWER_ABDOMEN}, took_painkiller=True, painkiller_helped=False))
    f = next(f for f in pain_findings(rec, date(2026, 6, 1)) if f.code == "painkillers_not_helping")
    assert f.severity is Severity.SOON


def test_bowel_or_sex_pain_pattern_and_worsening_pain():
    rec = record_from_lengths([28, 28, 28])
    for score, p in zip([4, 6, 8], rec.sorted_periods()[1:]):
        rec.pain.append(PainLog(p.start, score, {PainLocation.BOWEL}))
    found = {f.code for f in pain_findings(rec, date(2026, 6, 1))}
    assert {"pain_pattern_bowel_bladder_sex", "pain_worsening"} <= found


def test_relief_plan_never_doses_and_puts_warnings_first():
    rec = record_from_lengths([28])
    today = rec.last_period().start
    rec.pain.append(PainLog(today, 9, fever=True))
    plan = relief_plan(rec, today)
    assert plan["never_dose"] is True
    assert plan["warnings"][0].code == "pain_with_fever_or_discharge"
    assert plan["self_care"][0] == "heat"
