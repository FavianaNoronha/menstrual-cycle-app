"""Hard-coded safety rules. These never go through an LLM.

Every rule here must be signed off by the clinical advisor before release
(see docs/clinical/red-flags.md). Severity decides how the app reacts:
URGENT -> full-screen message with "seek care today"; SOON -> banner + doctor brief;
DISCUSS -> listed in the doctor brief; INFO -> shown in insights.
"""

from __future__ import annotations

from datetime import date

from .models import CycleRecord
from .norms import Finding, Severity, check_cycle_norms
from .pain import pain_findings
from .pbac import score_period
from .perimenopause import transition_hints

NO_PERIOD_DAYS = 90
POSTMENOPAUSE_GAP_DAYS = 365
HOURLY_SOAK_HOURS = 2


def bleeding_findings(record: CycleRecord, today: date) -> list[Finding]:
    findings: list[Finding] = []
    periods = record.sorted_periods()

    if record.soaking_hourly_hours >= HOURLY_SOAK_HOURS:
        findings.append(Finding("soaking_hourly", Severity.URGENT, {"hours": record.soaking_hourly_hours}))

    if record.profile.positive_pregnancy_test and periods and periods[-1].contains(today):
        findings.append(Finding("bleeding_with_positive_test", Severity.URGENT, {}))

    # Heavy flow pattern.
    scored = [
        score_period(record.flow, p.start, p.end or p.start) for p in periods[-3:] if p.end is not None
    ]
    heavy = [s for s in scored if s.heavy]
    if len(heavy) >= 2:
        findings.append(Finding("heavy_bleeding_pattern", Severity.SOON, {"pbac": [s.pbac for s in scored]}))
    elif len(heavy) == 1:
        findings.append(Finding("heavy_bleeding_once", Severity.INFO, {"pbac": [s.pbac for s in scored]}))

    # Bleeding after a year without periods.
    if len(periods) >= 2:
        gap = (periods[-1].start - periods[-2].start).days
        if gap >= POSTMENOPAUSE_GAP_DAYS and (record.profile.age or 0) >= 40:
            findings.append(Finding("bleeding_after_menopause", Severity.SOON, {"gap_days": gap}))

    # No period for 90+ days (and not known to be pregnant).
    if periods and not record.profile.positive_pregnancy_test:
        since = (today - periods[-1].start).days
        if NO_PERIOD_DAYS <= since < POSTMENOPAUSE_GAP_DAYS:
            findings.append(Finding("no_period_90_days", Severity.SOON, {"days": since}))

    return findings


_ORDER = {Severity.URGENT: 0, Severity.SOON: 1, Severity.DISCUSS: 2, Severity.INFO: 3}


def evaluate(record: CycleRecord, today: date) -> list[Finding]:
    """All findings, most severe first, de-duplicated by code."""
    all_findings = (
        bleeding_findings(record, today)
        + pain_findings(record, today)
        + check_cycle_norms(record)
        + transition_hints(record, today)
    )
    seen: set[str] = set()
    unique: list[Finding] = []
    for f in sorted(all_findings, key=lambda f: _ORDER[f.severity]):
        if f.code not in seen:
            seen.add(f.code)
            unique.append(f)
    return unique
