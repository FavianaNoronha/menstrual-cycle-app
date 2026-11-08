from datetime import date, timedelta

from helpers import record_from_lengths

from cycle_engine import FlowLog, Product, ProductUse, Saturation, Severity, check_cycle_norms, score_period


def codes(findings):
    return {f.code for f in findings}


def test_regular_normal_cycles_produce_no_findings():
    assert check_cycle_norms(record_from_lengths([28, 30, 27, 29])) == []


def test_irregularity_limit_depends_on_age():
    lengths = [26, 34, 28, 30]  # variation 8 days
    assert "cycles_irregular" in codes(check_cycle_norms(record_from_lengths(lengths, age=30)))
    assert "cycles_irregular" not in codes(check_cycle_norms(record_from_lengths(lengths, age=22)))


def test_infrequent_and_frequent_cycles_need_a_pattern():
    assert "cycles_infrequent" in codes(check_cycle_norms(record_from_lengths([45, 30, 50, 29])))
    assert "cycles_infrequent" not in codes(check_cycle_norms(record_from_lengths([45, 30, 29, 28])))
    assert "cycles_frequent" in codes(check_cycle_norms(record_from_lengths([21, 22, 28, 27])))


def test_prolonged_bleeding_is_flagged_soon():
    rec = record_from_lengths([28, 28, 28], bleed_days=10)
    finding = next(f for f in check_cycle_norms(rec) if f.code == "bleeding_prolonged")
    assert finding.severity is Severity.SOON


def _day(d, *items, small=0, large=0, flood=0):
    return FlowLog(day=d, items=list(items), small_clots=small, large_clots=large, flooding_episodes=flood)


def test_pbac_scoring_with_pads_and_clots():
    start = date(2026, 5, 1)
    full = ProductUse(Product.PAD, Saturation.FULL)
    mid = ProductUse(Product.PAD, Saturation.MEDIUM)
    logs = [
        _day(start, full, full, full, large=2),  # 60 + 10
        _day(start + timedelta(days=1), full, mid, small=1, flood=1),  # 25 + 1 + 5
        _day(start + timedelta(days=2), mid),  # 5
    ]
    score = score_period(logs, start, start + timedelta(days=4))
    assert score.pbac == 106
    assert score.heavy
    assert not score.low_certainty


def test_cup_millilitres_flag_heavy_above_80():
    start = date(2026, 5, 1)
    logs = [_day(start + timedelta(days=i), ProductUse(Product.CUP, cup_ml=30)) for i in range(3)]
    score = score_period(logs, start, start + timedelta(days=4))
    assert score.cup_ml == 90
    assert score.heavy


def test_mostly_cloth_is_low_certainty():
    start = date(2026, 5, 1)
    logs = [_day(start + timedelta(days=i), ProductUse(Product.CLOTH, Saturation.MEDIUM)) for i in range(4)]
    score = score_period(logs, start, start + timedelta(days=4))
    assert score.pbac == 20
    assert score.low_certainty
