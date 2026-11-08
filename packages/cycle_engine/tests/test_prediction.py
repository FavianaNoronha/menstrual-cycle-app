from datetime import date, timedelta

from helpers import record_from_lengths

from cycle_engine import Confidence, CycleRecord, Period, Window, cycle_window, predict_next_period


def test_no_periods_returns_none():
    assert predict_next_period(CycleRecord()) is None


def test_single_period_uses_typical_length_with_wide_low_confidence_range():
    rec = CycleRecord(periods=[Period(date(2026, 3, 1), date(2026, 3, 5))])
    pred = predict_next_period(rec, typical_cycle_days=30)
    assert pred.likely == date(2026, 3, 31)
    assert (pred.latest - pred.earliest).days == 14
    assert pred.confidence is Confidence.LOW
    assert pred.basis == "no_history"


def test_regular_cycles_give_tight_high_confidence_range():
    rec = record_from_lengths([28, 28, 29, 28, 27, 28, 28])
    pred = predict_next_period(rec)
    last = rec.last_period().start
    assert pred.likely == last + timedelta(days=28)
    assert pred.confidence is Confidence.HIGH
    assert (pred.latest - pred.earliest).days <= 4


def test_irregular_cycles_widen_the_range_and_lower_confidence():
    rec = record_from_lengths([26, 41, 33, 52, 29, 45])
    pred = predict_next_period(rec)
    assert pred.confidence is Confidence.LOW
    assert (pred.latest - pred.earliest).days > 10


def test_missed_period_gaps_are_not_used_as_cycle_lengths():
    rec = record_from_lengths([28, 28, 120, 28, 28])
    pred = predict_next_period(rec)
    assert pred.cycles_used == 4
    assert pred.likely == rec.last_period().start + timedelta(days=28)


def test_windows_are_relative_to_her_dates_not_hormonal_phases():
    rec = record_from_lengths([28, 28, 28, 28, 28, 28])
    start = rec.last_period().start
    assert cycle_window(rec, start + timedelta(days=1)).window is Window.BLEEDING
    assert cycle_window(rec, start + timedelta(days=8)).window is Window.BETWEEN
    assert cycle_window(rec, start + timedelta(days=14)).window is Window.BETWEEN  # no ovulation claim
    w = cycle_window(rec, start + timedelta(days=23))
    assert w.window is Window.BEFORE_PERIOD and w.days_to_expected == 5
    assert cycle_window(rec, start + timedelta(days=40)).window is Window.OVERDUE
    assert {m.value for m in Window}.isdisjoint({"luteal", "follicular", "ovulatory_estimate"})
