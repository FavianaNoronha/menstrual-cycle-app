"""PMS and mood tracking: symptom catalogue and "is it cyclical?" analysis.

Daily ratings use the DRSP 1-6 scale. The cyclicity check is inspired by
C-PASS (Eisenlohr-Moul et al., 2017) but simplified, and is NOT a diagnosis
of PMDD: it only tells the user whether a symptom rises before periods and
clears after, so she can bring that pattern to a doctor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from statistics import mean

from .models import CycleRecord

# Core daily items ("DRSP-lite"): fast enough to log in ~30 seconds.
CORE_ITEMS: dict[str, str] = {
    "mood_low": "Felt sad, low or hopeless",
    "anxiety": "Felt anxious or tense",
    "mood_swings": "Mood swings / suddenly tearful or sensitive",
    "irritability": "Irritable or angry",
    "cravings": "Food cravings or eating more",
    "energy_low": "Tired or low energy",
}

# Optional physical items users can switch on.
PHYSICAL_ITEMS: dict[str, str] = {
    "bloating": "Bloating",
    "breast_tenderness": "Breast tenderness or swelling",
    "headache": "Headache",
    "sleep_change": "Slept much more or much less",
    "acne": "Acne breakouts",
}

CRAVING_TYPES = ("sweet", "salty", "spicy", "fried", "carbs", "chocolate", "other")

PRE_WINDOW = range(-7, 0)  # 7 days before the next period start
POST_WINDOW = range(4, 11)  # cycle days 4-10, after bleeding usually settles
SCALE_RANGE = 5  # DRSP 1-6
MIN_ELEVATION = 0.30  # >= 30% of the scale range, as in C-PASS
MIN_DAYS_PER_WINDOW = 3


@dataclass(frozen=True)
class ItemPattern:
    item: str
    cycles_analyzed: int
    cycles_cyclical: int
    mean_pre: float | None
    mean_post: float | None

    @property
    def consistent(self) -> bool:
        """Cyclical in at least two analysed cycles and in most of them."""
        return self.cycles_cyclical >= 2 and self.cycles_cyclical * 2 > self.cycles_analyzed


def analyze_cyclicity(record: CycleRecord, items: list[str] | None = None) -> list[ItemPattern]:
    """For each item, check every complete cycle: does it rise premenstrually and clear after?"""
    periods = record.sorted_periods()
    by_day = {log.day: log for log in record.symptoms}
    items = items or list(CORE_ITEMS)
    results: list[ItemPattern] = []

    for item in items:
        analyzed = cyclical = 0
        pre_all: list[float] = []
        post_all: list[float] = []
        for current, nxt in zip(periods, periods[1:]):
            post_vals = [
                by_day[d].ratings[item]
                for offset in POST_WINDOW
                if (d := current.start + timedelta(days=offset - 1)) in by_day and item in by_day[d].ratings
            ]
            pre_vals = [
                by_day[d].ratings[item]
                for offset in PRE_WINDOW
                if (d := nxt.start + timedelta(days=offset)) in by_day and item in by_day[d].ratings
            ]
            if len(pre_vals) < MIN_DAYS_PER_WINDOW or len(post_vals) < MIN_DAYS_PER_WINDOW:
                continue
            analyzed += 1
            pre_m, post_m = mean(pre_vals), mean(post_vals)
            pre_all.extend(pre_vals)
            post_all.extend(post_vals)
            if (pre_m - post_m) / SCALE_RANGE >= MIN_ELEVATION and pre_m >= 3 and post_m <= 3:
                cyclical += 1
        results.append(
            ItemPattern(
                item=item,
                cycles_analyzed=analyzed,
                cycles_cyclical=cyclical,
                mean_pre=round(mean(pre_all), 2) if pre_all else None,
                mean_post=round(mean(post_all), 2) if post_all else None,
            )
        )
    return results


def top_cravings(record: CycleRecord, premenstrual_only: bool = True) -> dict[str, int]:
    """Count craving types, optionally only in the 7 days before each period."""
    periods = record.sorted_periods()
    pre_days = set()
    for p in periods[1:]:
        for offset in PRE_WINDOW:
            pre_days.add(p.start + timedelta(days=offset))
    counts: dict[str, int] = {}
    for log in record.symptoms:
        if premenstrual_only and log.day not in pre_days:
            continue
        for kind in log.craving_types:
            counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))
