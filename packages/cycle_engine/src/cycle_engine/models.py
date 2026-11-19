"""Core data types for the cycle record.

Everything here is plain dataclasses so the engine has no dependencies and can
run on the server, in tests, or be ported to Dart for on-device use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum


class Product(str, Enum):
    """Menstrual products a user can log. Cloth is common in India."""

    PAD = "pad"
    TAMPON = "tampon"
    CLOTH = "cloth"
    CUP = "cup"
    PERIOD_UNDERWEAR = "period_underwear"


class Saturation(str, Enum):
    """How soaked a pad, cloth or tampon was when changed (PBAC pictogram rows)."""

    LIGHT = "light"  # lightly stained
    MEDIUM = "medium"  # moderately soiled
    FULL = "full"  # completely saturated


@dataclass(frozen=True)
class ProductUse:
    product: Product
    saturation: Saturation | None = None
    cup_ml: float | None = None  # cups have measurement lines; users can read mL directly


@dataclass
class FlowLog:
    day: date
    items: list[ProductUse] = field(default_factory=list)
    small_clots: int = 0  # smaller than a 1-rupee coin
    large_clots: int = 0  # about a 10-rupee coin or larger
    flooding_episodes: int = 0  # leaked through / soaked clothes
    level: str | None = None  # quick log ("light" / "medium" / "heavy") when products weren't counted


@dataclass
class Period:
    """A bleeding episode. `end` is inclusive; None while still ongoing."""

    start: date
    end: date | None = None

    def length_days(self) -> int | None:
        if self.end is None:
            return None
        return (self.end - self.start).days + 1

    def contains(self, day: date) -> bool:
        if day < self.start:
            return False
        return self.end is None or day <= self.end


@dataclass
class SymptomLog:
    """Daily symptom ratings on the DRSP 1-6 scale (1 = not at all, 6 = extreme)."""

    day: date
    ratings: dict[str, int] = field(default_factory=dict)
    craving_types: set[str] = field(default_factory=set)  # e.g. {"sweet", "salty", "spicy"}

    def __post_init__(self) -> None:
        for item, value in self.ratings.items():
            if not 1 <= value <= 6:
                raise ValueError(f"rating for {item!r} must be 1-6, got {value}")


class PainLocation(str, Enum):
    LOWER_ABDOMEN = "lower_abdomen"
    LOWER_BACK = "lower_back"
    THIGHS = "thighs"
    ONE_SIDE = "one_side"
    BOWEL = "bowel"  # pain passing stool
    BLADDER = "bladder"  # pain passing urine
    DURING_SEX = "during_sex"
    HEAD = "head"


class Impact(str, Enum):
    """What the pain stopped her doing (functional impact)."""

    WORK = "work"
    SCHOOL = "school"
    SLEEP = "sleep"
    EXERCISE = "exercise"
    HOUSEWORK = "housework"


@dataclass
class PainLog:
    day: date
    score: int  # 0-10 numeric rating scale
    locations: set[PainLocation] = field(default_factory=set)
    took_painkiller: bool = False
    painkiller_helped: bool | None = None
    fever: bool = False
    fainted_or_dizzy: bool = False
    unusual_discharge: bool = False
    duration_minutes: int | None = None  # how long the pain lasted that day, if she knows
    nausea_vomiting: bool = False
    impacts: set[Impact] = field(default_factory=set)  # activities she missed or couldn't do

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 10:
            raise ValueError(f"pain score must be 0-10, got {self.score}")
        if self.duration_minutes is not None and self.duration_minutes < 0:
            raise ValueError("duration_minutes cannot be negative")


@dataclass(frozen=True)
class SleepLog:
    day: date  # the morning the sleep is logged for
    hours: float

    def __post_init__(self) -> None:
        if not 0 <= self.hours <= 24:
            raise ValueError(f"sleep hours must be 0-24, got {self.hours}")


@dataclass
class Treatment:
    """Something she started: a clinician-recommended medicine, therapy or a self-care habit.

    The engine only compares what she logged before and after `started`. It never
    suggests a treatment and never claims the treatment caused a change.
    """

    name: str
    started: date
    clinician_recommended: bool = False
    stopped: date | None = None
    side_effects: bool = False


@dataclass
class Profile:
    age: int | None = None
    pregnancy_possible: bool | None = None
    positive_pregnancy_test: bool = False
    language: str = "en"  # en, hi, kn, te, ta


@dataclass
class CycleRecord:
    """Everything the engine needs about one person."""

    periods: list[Period] = field(default_factory=list)
    flow: list[FlowLog] = field(default_factory=list)
    symptoms: list[SymptomLog] = field(default_factory=list)
    pain: list[PainLog] = field(default_factory=list)
    sleep: list[SleepLog] = field(default_factory=list)
    treatments: list[Treatment] = field(default_factory=list)
    profile: Profile = field(default_factory=Profile)
    soaking_hourly_hours: int = 0  # hours in a row a pad was soaked within an hour (latest episode)
    prediction_misses: int = 0  # times she told us "that prediction was wrong"; each widens the range

    def sorted_periods(self) -> list[Period]:
        return sorted(self.periods, key=lambda p: p.start)

    def cycle_lengths(self) -> list[int]:
        """Days between consecutive period starts, oldest first."""
        starts = [p.start for p in self.sorted_periods()]
        return [(b - a).days for a, b in zip(starts, starts[1:])]

    def last_period(self) -> Period | None:
        periods = self.sorted_periods()
        return periods[-1] if periods else None

    def cycle_day(self, day: date) -> int | None:
        """Cycle day (1 = first day of bleeding) for `day`, using the latest period start on or before it."""
        starts = [p.start for p in self.sorted_periods() if p.start <= day]
        if not starts:
            return None
        return (day - starts[-1]).days + 1


def daterange(start: date, end: date):
    """Inclusive date range."""
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)
