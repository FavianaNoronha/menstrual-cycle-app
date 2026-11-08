from datetime import date, timedelta

from cycle_engine import CycleRecord, Period, Profile


def periods_from_lengths(start: date, lengths: list[int], bleed_days: int = 5) -> list[Period]:
    """Build periods whose starts are separated by `lengths`."""
    periods = []
    current = start
    for n in [0] + lengths:
        current = current + timedelta(days=n)
        periods.append(Period(start=current, end=current + timedelta(days=bleed_days - 1)))
    return periods


def record_from_lengths(lengths: list[int], age: int | None = 30, bleed_days: int = 5) -> CycleRecord:
    return CycleRecord(
        periods=periods_from_lengths(date(2026, 1, 1), lengths, bleed_days),
        profile=Profile(age=age),
    )
