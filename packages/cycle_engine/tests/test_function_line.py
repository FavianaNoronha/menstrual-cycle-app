from datetime import date, timedelta

from helpers import record_from_lengths

from cycle_engine import Impact, PainLog, build_brief, function_line, pain_plan, render_text
from cycle_engine.pain import DEFAULT_LINE


def _log(rec, scores_with_impact):
    """One pain log on the first day of each period; (score, lost_function) per period."""
    for p, (score, lost) in zip(rec.sorted_periods(), scores_with_impact):
        rec.pain.append(PainLog(p.start, score, impacts={Impact.WORK} if lost else set()))


def test_default_line_until_two_cycles_with_impact():
    rec = record_from_lengths([28, 28, 28])
    assert function_line(rec).source == "default" and function_line(rec).score == DEFAULT_LINE
    _log(rec, [(5, True), (3, False), (4, False)])
    fl = function_line(rec)
    assert fl.source == "default" and fl.cycles_used == 1  # one cycle is not enough to personalise


def test_personal_line_is_median_of_lowest_impact_score_per_cycle():
    rec = record_from_lengths([28, 28, 28, 28])
    _log(rec, [(5, True), (7, True), (4, True), (3, False)])
    fl = function_line(rec)
    assert (fl.score, fl.source, fl.cycles_used) == (5, "personal", 3)


def test_line_is_clamped():
    rec = record_from_lengths([28, 28, 28])
    _log(rec, [(1, True), (1, True), (1, True)])
    assert function_line(rec).score == 3


def test_nudge_due_two_days_before_when_pain_repeatedly_crosses_line():
    rec = record_from_lengths([28, 28, 28, 28])
    _log(rec, [(5, True), (6, True), (7, True), (8, True)])  # personal line 6; last 3 cycles peak 6,7,8
    day = rec.last_period().start + timedelta(days=26)
    plan = pain_plan(rec, day)
    assert plan.repeats and plan.cycles_over_line == 3 and plan.nudge_due
    assert not pain_plan(rec, rec.last_period().start + timedelta(days=15)).nudge_due  # mid-cycle: no nudge
    assert pain_plan(rec, rec.last_period().start + timedelta(days=15)).repeats  # but PLAN still shows the pattern


def test_no_nudge_when_pain_stays_below_line():
    rec = record_from_lengths([28, 28, 28, 28])
    _log(rec, [(5, True), (6, True), (3, False), (4, False)])  # line 6; recent peaks 6,3,4 -> only 1 over
    plan = pain_plan(rec, rec.last_period().start + timedelta(days=26))
    assert not plan.repeats and not plan.nudge_due


def test_no_nudge_without_pain_history():
    rec = record_from_lengths([28, 28, 28])
    assert not pain_plan(rec, rec.last_period().start + timedelta(days=26)).nudge_due


def test_brief_shows_the_line_and_says_where_it_came_from():
    rec = record_from_lengths([28, 28, 28, 28])
    _log(rec, [(5, True), (7, True), (4, True), (6, True)])
    text = render_text(build_brief(rec, date(2027, 1, 1)))
    assert "stop her daily activities" in text and "from her own logs" in text
