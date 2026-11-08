"""Next-period prediction as an honest range, not a single date.

Calendar apps average past cycles and show one date; that fails people with
irregular cycles. We show a range whose width reflects her own variability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from statistics import median

from .models import CycleRecord

DEFAULT_CYCLE_DAYS = 28
MAX_HISTORY = 12  # recent cycles matter most; older ones may reflect a different life stage
OUTLIER_DAYS = 90  # gaps this long are treated as a missed-period episode, not a "cycle length"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class Prediction:
    earliest: date
    likely: date
    latest: date
    confidence: Confidence
    cycles_used: int
    basis: str  # machine-readable explanation key for the UI


def _percentile(sorted_values: list[float], q: float) -> float:
    """Linear-interpolated percentile, q in [0, 1]."""
    if not sorted_values:
        raise ValueError("empty")
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = pos - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def predict_next_period(record: CycleRecord, typical_cycle_days: int | None = None) -> Prediction | None:
    """Predict the next period start as a range.

    - 0 cycles of history: use the user's stated typical length (or 28) with a wide, low-confidence range.
    - 1-3 cycles: median with min/max widened by 2 days.
    - 4+ cycles: median with the 10th-90th percentile range.
    """
    last = record.last_period()
    if last is None:
        return None

    lengths = [n for n in record.cycle_lengths() if n < OUTLIER_DAYS][-MAX_HISTORY:]

    if not lengths:
        base = typical_cycle_days or DEFAULT_CYCLE_DAYS
        return Prediction(
            earliest=last.start + timedelta(days=base - 7),
            likely=last.start + timedelta(days=base),
            latest=last.start + timedelta(days=base + 7),
            confidence=Confidence.LOW,
            cycles_used=0,
            basis="no_history",
        )

    values = sorted(float(n) for n in lengths)
    mid = median(values)
    if len(values) >= 4:
        lo, hi = _percentile(values, 0.10), _percentile(values, 0.90)
        basis = "percentile_range"
    else:
        lo, hi = values[0] - 2, values[-1] + 2
        basis = "min_max_widened"

    spread = hi - lo
    if len(values) >= 6 and spread <= 4:
        confidence = Confidence.HIGH
    elif len(values) >= 3 and spread <= 8:
        confidence = Confidence.MEDIUM
    else:
        confidence = Confidence.LOW

    return Prediction(
        earliest=last.start + timedelta(days=round(lo)),
        likely=last.start + timedelta(days=round(mid)),
        latest=last.start + timedelta(days=round(hi)),
        confidence=confidence,
        cycles_used=len(values),
        basis=basis,
    )


class Phase(str, Enum):
    MENSTRUAL = "menstrual"
    FOLLICULAR = "follicular"
    OVULATORY_ESTIMATE = "ovulatory_estimate"
    LUTEAL = "luteal"
    PREMENSTRUAL = "premenstrual"  # last ~7 days before the next period
    LATE = "late"  # past the latest predicted date
    UNKNOWN = "unknown"


def estimate_phase(record: CycleRecord, day: date) -> Phase:
    """Rough phase estimate from the calendar. Labelled an estimate everywhere in the UI.

    The luteal phase is fairly stable (~14 days), so ovulation is estimated as
    14 days before the likely next period. Without temperature or hormone data
    this is a guess, and it is meaningless for people who don't ovulate.
    """
    last = record.last_period()
    if last is None or day < last.start:
        return Phase.UNKNOWN
    if last.contains(day) and (last.end is not None or (day - last.start).days < 8):
        return Phase.MENSTRUAL

    pred = predict_next_period(record)
    if pred is None:
        return Phase.UNKNOWN
    if day > pred.latest:
        return Phase.LATE

    days_to_next = (pred.likely - day).days
    if days_to_next <= 7:
        return Phase.PREMENSTRUAL
    if 12 <= days_to_next <= 16:
        return Phase.OVULATORY_ESTIMATE
    if days_to_next < 12:
        return Phase.LUTEAL
    return Phase.FOLLICULAR
