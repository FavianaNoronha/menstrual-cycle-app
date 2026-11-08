"""Compare a person's cycles with clinical norms (FIGO AUB System 1, 2018).

FIGO normal limits used here:
- Frequency: 24-38 days between period starts.
- Regularity: shortest-to-longest cycle variation <= 7 days (ages 26-41)
  or <= 9 days (ages 18-25 and 42-45).
- Duration: bleeding lasts <= 8 days.
- Volume: heavy if PBAC > 100 (see pbac.py).

Findings are phrased as "outside the typical range", never as a diagnosis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .models import CycleRecord
from .prediction import OUTLIER_DAYS

FREQ_MIN, FREQ_MAX = 24, 38
DURATION_MAX = 8


class Severity(str, Enum):
    INFO = "info"  # worth knowing
    DISCUSS = "discuss"  # mention at the next doctor visit
    SOON = "soon"  # book a doctor visit in the coming weeks
    URGENT = "urgent"  # seek care today


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    evidence: dict = field(default_factory=dict)


def regularity_limit_days(age: int | None) -> int:
    if age is not None and 26 <= age <= 41:
        return 7
    return 9


def check_cycle_norms(record: CycleRecord, min_cycles: int = 3) -> list[Finding]:
    findings: list[Finding] = []
    lengths = [n for n in record.cycle_lengths() if n < OUTLIER_DAYS]

    if len(lengths) >= min_cycles:
        recent = lengths[-6:]
        short = [n for n in recent if n < FREQ_MIN]
        long = [n for n in recent if n > FREQ_MAX]
        # Require a pattern (2+ cycles), not a one-off.
        if len(short) >= 2:
            findings.append(Finding("cycles_frequent", Severity.DISCUSS, {"lengths": recent, "below": FREQ_MIN}))
        if len(long) >= 2:
            findings.append(Finding("cycles_infrequent", Severity.DISCUSS, {"lengths": recent, "above": FREQ_MAX}))

        variation = max(recent) - min(recent)
        limit = regularity_limit_days(record.profile.age)
        if variation > limit:
            findings.append(
                Finding("cycles_irregular", Severity.DISCUSS, {"variation_days": variation, "limit_days": limit})
            )

    long_bleeds = [p for p in record.sorted_periods()[-6:] if (p.length_days() or 0) > DURATION_MAX]
    if len(long_bleeds) >= 2:
        findings.append(
            Finding(
                "bleeding_prolonged",
                Severity.SOON,
                {"lengths": [p.length_days() for p in long_bleeds], "limit_days": DURATION_MAX},
            )
        )
    return findings
