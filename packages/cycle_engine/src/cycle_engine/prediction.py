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
    irregular: bool = False  # her cycles vary too much for a single date to mean much


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


IRREGULAR_SPREAD_DAYS = 9  # longest minus shortest cycle; ACOG/FIGO treat >7-9 days variation as irregular
NORMAL_CYCLE_RANGE = (21, 38)  # FIGO 2018 normal inter-menstrual interval
MISS_WIDEN_DAYS = 2  # each "prediction was wrong" press widens the range by this much per side
MAX_MISS_WIDEN = 3  # at most 3 presses count, so a few taps can't make the range meaningless


def is_irregular(lengths: list[int]) -> bool:
    """3+ cycles that vary a lot or sit outside the normal 21-38 day interval."""
    if len(lengths) < 3:
        return False
    return (max(lengths) - min(lengths) >= IRREGULAR_SPREAD_DAYS
            or any(n < NORMAL_CYCLE_RANGE[0] or n > NORMAL_CYCLE_RANGE[1] for n in lengths))


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
    irregular = is_irregular(lengths)
    if irregular:
        # Percentiles hide the extremes; for irregular cycles show everything she has actually had.
        lo, hi = values[0], values[-1]
        basis = "irregular_full_range"
    elif len(values) >= 4:
        lo, hi = _percentile(values, 0.10), _percentile(values, 0.90)
        basis = "percentile_range"
    else:
        lo, hi = values[0] - 2, values[-1] + 2
        basis = "min_max_widened"

    widen = MISS_WIDEN_DAYS * min(record.prediction_misses, MAX_MISS_WIDEN)
    lo, hi = lo - widen, hi + widen
    spread = hi - lo
    if irregular or record.prediction_misses:
        confidence = Confidence.LOW
    elif len(values) >= 6 and spread <= 4:
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
        irregular=irregular,
    )


class Window(str, Enum):
    """Where a day sits relative to her own period dates.

    Deliberately NOT hormonal phases. Counting days cannot tell whether or when
    someone ovulated (BMJ analysis, Sept 2026), so we never say "luteal" or
    "ovulatory". We only say how far a day is from her expected next period.
    """

    BLEEDING = "bleeding"
    BEFORE_PERIOD = "before_period"  # the 7 days before the likely start
    BETWEEN = "between"
    OVERDUE = "overdue"  # past the latest predicted date
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CycleWindow:
    window: Window
    days_to_expected: int | None  # negative once past the likely date


def cycle_window(record: CycleRecord, day: date) -> CycleWindow:
    last = record.last_period()
    if last is None or day < last.start:
        return CycleWindow(Window.UNKNOWN, None)
    pred = predict_next_period(record)
    days_to = (pred.likely - day).days if pred else None
    if last.contains(day) and (last.end is not None or (day - last.start).days < 8):
        return CycleWindow(Window.BLEEDING, days_to)
    if pred is None:
        return CycleWindow(Window.UNKNOWN, None)
    if day > pred.latest:
        return CycleWindow(Window.OVERDUE, days_to)
    if days_to is not None and days_to <= 7:
        return CycleWindow(Window.BEFORE_PERIOD, days_to)
    return CycleWindow(Window.BETWEEN, days_to)
