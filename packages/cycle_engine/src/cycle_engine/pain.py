"""Period pain: evidence-based self-care guide and pain-specific warning signs.

Content rules (enforced in review, see docs/clinical/pain-relief.md):
- Never give medicine doses. Point to the pack label or a pharmacist.
- Every self-care card carries its evidence level and source.
- Warning signs always outrank self-care: if any are present, show them first.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean, median

from .models import CycleRecord, PainLocation, PainLog, Treatment
from .norms import Finding, Severity
from .prediction import Window, cycle_window


@dataclass(frozen=True)
class SelfCareOption:
    key: str
    evidence: str  # "strong", "moderate", "some"
    source: str


# Ordered by strength of evidence. Text lives in i18n keyed by `key`.
SELF_CARE: tuple[SelfCareOption, ...] = (
    SelfCareOption(
        "heat",
        "strong",
        "Yuan et al. 2026, Front Med (57 RCTs): heat reduces period pain; similar relief to NSAIDs with fewer side effects",
    ),
    SelfCareOption(
        "painkiller_nsaid",
        "strong",
        "NICE CKS dysmenorrhoea: NSAIDs are first-line for primary dysmenorrhoea unless contraindicated",
    ),
    SelfCareOption(
        "movement",
        "moderate",
        "Armour et al. 2019, BMC Complement Altern Med (23 trials): exercise showed the largest effect among self-care options",
    ),
    SelfCareOption("tens", "moderate", "NICE CKS dysmenorrhoea: high-frequency TENS is an option"),
    SelfCareOption(
        "ginger",
        "some",
        "Review of reviews (21 systematic reviews): ginger had the most consistent evidence among supplements",
    ),
    SelfCareOption("rest_breathing", "some", "Common self-care; low risk; helps sleep and coping"),
)

SEVERE = 8
PAINKILLER_FAIL_CYCLES = 3


def _period_days(record: CycleRecord, lookahead_before: int = 2) -> set[date]:
    """Days within a period, plus a couple of days before it (cramps often start early)."""
    days: set[date] = set()
    for p in record.sorted_periods():
        end = p.end or (p.start + timedelta(days=6))
        d = p.start - timedelta(days=lookahead_before)
        while d <= end:
            days.add(d)
            d += timedelta(days=1)
    return days


def _pain_by_period(record: CycleRecord) -> list[list]:
    """Group pain logs by the period they fall in (oldest first)."""
    groups = []
    for p in record.sorted_periods():
        end = p.end or (p.start + timedelta(days=6))
        groups.append([log for log in record.pain if p.start - timedelta(days=2) <= log.day <= end])
    return groups


def pain_findings(record: CycleRecord, today: date) -> list[Finding]:
    findings: list[Finding] = []
    recent = [log for log in record.pain if (today - log.day).days <= 3]

    # Same-day danger signs.
    for log in recent:
        if log.fainted_or_dizzy:
            findings.append(Finding("pain_with_fainting", Severity.URGENT, {"day": log.day.isoformat()}))
        if PainLocation.ONE_SIDE in log.locations and (
            record.profile.positive_pregnancy_test or record.profile.pregnancy_possible
        ):
            findings.append(Finding("one_sided_pain_pregnancy_possible", Severity.URGENT, {"day": log.day.isoformat()}))
        if log.fever or log.unusual_discharge:
            sev = Severity.URGENT if log.score >= SEVERE else Severity.SOON
            findings.append(Finding("pain_with_fever_or_discharge", sev, {"day": log.day.isoformat()}))

    groups = [g for g in _pain_by_period(record) if g]

    # Painkillers not helping across cycles.
    fail_cycles = sum(1 for g in groups if any(l.took_painkiller and l.painkiller_helped is False for l in g))
    if fail_cycles >= PAINKILLER_FAIL_CYCLES:
        findings.append(Finding("painkillers_not_helping", Severity.SOON, {"cycles": fail_cycles}))

    # Endometriosis-pattern symptoms (pain with sex, bowel or bladder) in 2+ cycles.
    pattern_locs = {PainLocation.DURING_SEX, PainLocation.BOWEL, PainLocation.BLADDER}
    pattern_cycles = sum(1 for g in groups if any(l.locations & pattern_locs for l in g))
    if pattern_cycles >= 2:
        findings.append(Finding("pain_pattern_bowel_bladder_sex", Severity.DISCUSS, {"cycles": pattern_cycles}))

    # Pain outside periods (acyclic) on 3+ days in the last 60 days.
    period_days = _period_days(record)
    acyclic = [l for l in record.pain if (today - l.day).days <= 60 and l.score >= 4 and l.day not in period_days]
    if len(acyclic) >= 3:
        findings.append(Finding("pain_outside_periods", Severity.DISCUSS, {"days": len(acyclic)}))

    # Worsening: peak period pain rising by 2+ points across the last 3 cycles.
    peaks = [max(l.score for l in g) for g in groups][-3:]
    if len(peaks) == 3 and peaks[0] < peaks[1] < peaks[2] and peaks[2] - peaks[0] >= 2:
        findings.append(Finding("pain_worsening", Severity.DISCUSS, {"peaks": peaks}))

    # Pain stopped her doing things in 2+ cycles.
    impact_cycles = sum(1 for g in groups if any(l.impacts for l in g))
    if impact_cycles >= 2:
        findings.append(Finding("pain_disrupting_daily_life", Severity.DISCUSS, {"cycles": impact_cycles}))

    # Severe pain in 2+ cycles.
    severe_cycles = sum(1 for g in groups if max(l.score for l in g) >= SEVERE)
    if severe_cycles >= 2:
        findings.append(Finding("pain_severe_recurrent", Severity.DISCUSS, {"cycles": severe_cycles}))

    return findings


def _timing(record: CycleRecord, log: PainLog) -> str:
    """'before' = up to 7 days before a period start, 'during', or 'outside'."""
    for p in record.sorted_periods():
        end = p.end or (p.start + timedelta(days=6))
        if p.start <= log.day <= end:
            return "during"
        if 0 < (p.start - log.day).days <= 7:
            return "before"
    return "outside"


def _flag_rate(logs: list[PainLog], attr: str) -> float | None:
    return round(sum(1 for l in logs if getattr(l, attr)) / len(logs), 2) if logs else None


def treatment_response(record: CycleRecord, treatment: Treatment, min_cycles: int = 2) -> dict:
    """Compare logged pain before vs after a treatment started. Observed change only, never cause.

    Needs `min_cycles` periods with pain logs on each side; otherwise says so.
    """
    before, after = [], []
    for p in record.sorted_periods():
        end = p.end or (p.start + timedelta(days=6))
        logs = [l for l in record.pain if p.start - timedelta(days=2) <= l.day <= end]
        if not logs:
            continue
        (before if end < treatment.started else after if p.start >= treatment.started else []).append(logs)
    result = {
        "treatment": treatment.name,
        "started": treatment.started.isoformat(),
        "clinician_recommended": treatment.clinician_recommended,
        "side_effects_reported": treatment.side_effects,
        "cycles_before": len(before),
        "cycles_after": len(after),
        "note": "Observed change in her own logs. It does not show the treatment caused it; ask her doctor.",
    }
    if len(before) < min_cycles or len(after) < min_cycles:
        return {**result, "status": "not_enough_cycles"}

    def peak(groups):
        return round(mean(max(l.score for l in g) for g in groups), 1)

    def impact_days(groups):
        return round(mean(sum(1 for l in g if l.impacts) for g in groups), 1)

    pb, pa = peak(before), peak(after)
    return {
        **result,
        "status": "ok",
        "average_peak_before": pb,
        "average_peak_after": pa,
        "peak_change": round(pa - pb, 1),
        "impact_days_per_cycle_before": impact_days(before),
        "impact_days_per_cycle_after": impact_days(after),
    }


# ---- her personal "function line" ----------------------------------------------
# The pain score at which pain starts to stop HER doing things. Interference studies
# put the moderate band around 5-6 and severe at 7+, but individual cut-offs vary
# (some people lose function at 4, others at 8), so 6 is only a starting point that
# her own logs replace. This is a planning aid, never a target to "tolerate more":
# recurrent period pain is itself a reason to see a doctor.
DEFAULT_LINE = 6
MIN_CYCLES_FOR_PERSONAL = 2
LINE_FLOOR, LINE_CEILING = 3, 9


@dataclass(frozen=True)
class FunctionLine:
    score: int
    source: str  # "default" or "personal"
    cycles_used: int


def function_line(record: CycleRecord) -> FunctionLine:
    """Median, across cycles, of the lowest pain score on a day pain stopped her doing something."""
    groups = [g for g in _pain_by_period(record) if g]
    lowest = [min(l.score for l in g if l.impacts) for g in groups if any(l.impacts for l in g)]
    if len(lowest) < MIN_CYCLES_FOR_PERSONAL:
        return FunctionLine(DEFAULT_LINE, "default", len(lowest))
    score = max(LINE_FLOOR, min(LINE_CEILING, round(median(lowest))))
    return FunctionLine(score, "personal", len(lowest))


@dataclass(frozen=True)
class PainPlan:
    line: FunctionLine
    cycles_over_line: int  # of her last 3 cycles with pain logs, how many peaked at or above the line
    cycles_considered: int
    days_to_expected: int | None
    repeats: bool  # at or above the line in 2+ recent cycles: suggest a doctor
    nudge_due: bool  # 0-2 days before her expected period AND it repeats


def pain_plan(record: CycleRecord, today: date) -> PainPlan:
    """What the PLAN command shows, and when the bot adds a heads-up before her period."""
    line = function_line(record)
    groups = [g for g in _pain_by_period(record) if g][-3:]
    over = sum(1 for g in groups if max(l.score for l in g) >= line.score)
    repeats = over >= 2
    cw = cycle_window(record, today)
    due = repeats and cw.window is Window.BEFORE_PERIOD and cw.days_to_expected is not None and 0 <= cw.days_to_expected <= 2
    return PainPlan(line, over, len(groups), cw.days_to_expected, repeats, due)


def _sleep_on_bad_days(record: CycleRecord) -> dict | None:
    """Average sleep the night before high-pain days vs other days (needs 3+ of each)."""
    by_day = {s.day: s.hours for s in record.sleep}
    bad_days = {l.day for l in record.pain if l.score >= 6}
    bad = [by_day[d] for d in bad_days if d in by_day]
    other = [h for d, h in by_day.items() if d not in bad_days]
    if len(bad) < 3 or len(other) < 3:
        return None
    return {"high_pain_days_avg_hours": round(mean(bad), 1), "other_days_avg_hours": round(mean(other), 1)}


def pain_summary(record: CycleRecord) -> dict:
    groups = [g for g in _pain_by_period(record) if g]
    peaks = [max(l.score for l in g) for g in groups]
    logs = record.pain
    timing = {"before": 0, "during": 0, "outside": 0}
    for l in logs:
        timing[_timing(record, l)] += 1
    durations = [l.duration_minutes for l in logs if l.duration_minutes is not None]
    impacts: dict[str, int] = {}
    for l in logs:
        for i in l.impacts:
            impacts[i.value] = impacts.get(i.value, 0) + 1
    return {
        "cycles_with_pain_logs": len(groups),
        "peak_pain_by_cycle": peaks[-6:],
        "average_peak": round(mean(peaks), 1) if peaks else None,
        "painkiller_helped_rate": _helped_rate(record),
        "pain_days_by_timing": timing,
        "typical_duration_minutes": sorted(durations)[len(durations) // 2] if durations else None,
        "nausea_or_vomiting_rate": _flag_rate(logs, "nausea_vomiting"),
        "days_activity_missed": impacts,
        "sleep_on_high_pain_days": _sleep_on_bad_days(record),
        "function_line": function_line(record).__dict__,
        "treatments": [treatment_response(record, t) for t in record.treatments],
    }


def _helped_rate(record: CycleRecord) -> float | None:
    taken = [l for l in record.pain if l.took_painkiller and l.painkiller_helped is not None]
    if not taken:
        return None
    return round(sum(1 for l in taken if l.painkiller_helped) / len(taken), 2)


def relief_plan(record: CycleRecord, today: date) -> dict:
    """What the 'My cramps are bad' screen shows: warning signs first, then self-care by evidence."""
    warnings = [f for f in pain_findings(record, today) if f.severity in (Severity.URGENT, Severity.SOON)]
    return {
        "warnings": warnings,
        "self_care": [opt.key for opt in SELF_CARE],
        "never_dose": True,
    }
