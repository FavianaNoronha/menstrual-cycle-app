"""Menopause-transition hints from cycle data, after STRAW+10 (Harlow et al., 2012).

- Early transition: persistent >= 7-day difference in length of consecutive cycles
  (persistent = happens again within 10 cycles).
- Late transition: a gap of >= 60 days without a period.
- Menopause: 12 months without a period (only knowable in hindsight).

Indian women reach menopause around age 46 on average (IMS pan-India survey),
so hints start at 35 rather than the mid-40s many Western apps assume.
"""

from __future__ import annotations

from datetime import date

from .models import CycleRecord
from .norms import Finding, Severity

MIN_AGE = 35


def transition_hints(record: CycleRecord, today: date) -> list[Finding]:
    age = record.profile.age
    if age is None or age < MIN_AGE:
        return []

    findings: list[Finding] = []
    lengths = record.cycle_lengths()[-10:]
    big_jumps = sum(1 for a, b in zip(lengths, lengths[1:]) if abs(a - b) >= 7)
    if big_jumps >= 2:
        findings.append(Finding("transition_early_signs", Severity.DISCUSS, {"jumps": big_jumps}))

    gaps = [n for n in record.cycle_lengths() if n >= 60]
    last = record.last_period()
    open_gap = (today - last.start).days if last else None
    if gaps or (open_gap is not None and 60 <= open_gap < 365):
        findings.append(
            Finding("transition_late_signs", Severity.DISCUSS, {"longest_gap_days": max(gaps + [open_gap or 0])})
        )

    if open_gap is not None and open_gap >= 365:
        findings.append(Finding("possible_menopause", Severity.INFO, {"days_since_last_period": open_gap}))

    return findings
