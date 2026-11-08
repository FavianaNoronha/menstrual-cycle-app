"""Pictorial Blood loss Assessment Chart (PBAC) scoring, adapted for India.

Scoring follows Higham et al. (1990):
- Pads (and cloth, by assumption): lightly stained 1, moderately soiled 5, fully saturated 20.
- Tampons: 1, 5, 10.
- Clots: small 1, large 5.  Flooding (leak through clothes): 5 per episode.
A cycle total above 100 is the usual threshold for heavy menstrual bleeding.

India adaptations (to validate with the clinical advisor):
- Cloth is scored like a pad. Cloth size varies a lot, so cloth-heavy cycles are flagged as lower certainty.
- Clot size references use coins people carry: small = smaller than a 1-rupee coin, large = about a 10-rupee coin.
- Menstrual cup users read millilitres directly; > 80 mL per cycle is heavy bleeding by definition.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .models import FlowLog, Product, Saturation

PAD_POINTS = {Saturation.LIGHT: 1, Saturation.MEDIUM: 5, Saturation.FULL: 20}
TAMPON_POINTS = {Saturation.LIGHT: 1, Saturation.MEDIUM: 5, Saturation.FULL: 10}
SMALL_CLOT, LARGE_CLOT, FLOODING = 1, 5, 5
HEAVY_PBAC = 100
HEAVY_ML = 80.0


@dataclass(frozen=True)
class FlowScore:
    pbac: int
    cup_ml: float
    heavy: bool
    low_certainty: bool  # e.g. mostly cloth, or mixed products
    days: int


def score_day(log: FlowLog) -> tuple[int, float, bool]:
    """Return (pbac points, cup mL, used_cloth) for one day."""
    points = 0
    ml = 0.0
    used_cloth = False
    for use in log.items:
        if use.product in (Product.PAD, Product.CLOTH, Product.PERIOD_UNDERWEAR):
            if use.saturation is not None:
                points += PAD_POINTS[use.saturation]
            used_cloth = used_cloth or use.product is Product.CLOTH
        elif use.product is Product.TAMPON:
            if use.saturation is not None:
                points += TAMPON_POINTS[use.saturation]
        elif use.product is Product.CUP and use.cup_ml is not None:
            ml += max(0.0, use.cup_ml)
    points += log.small_clots * SMALL_CLOT + log.large_clots * LARGE_CLOT + log.flooding_episodes * FLOODING
    return points, ml, used_cloth


def score_period(flow_logs: list[FlowLog], start: date, end: date) -> FlowScore:
    """Score all flow logs that fall within one period (inclusive dates)."""
    in_period = [log for log in flow_logs if start <= log.day <= end]
    total_points, total_ml, cloth_days = 0, 0.0, 0
    products_seen: set[Product] = set()
    for log in in_period:
        points, ml, used_cloth = score_day(log)
        total_points += points
        total_ml += ml
        cloth_days += int(used_cloth)
        products_seen.update(u.product for u in log.items)

    heavy = total_points > HEAVY_PBAC or total_ml > HEAVY_ML
    mixed_cup = Product.CUP in products_seen and len(products_seen) > 1
    low_certainty = (in_period and cloth_days >= len(in_period) / 2) or mixed_cup
    return FlowScore(
        pbac=total_points,
        cup_ml=round(total_ml, 1),
        heavy=heavy,
        low_certainty=bool(low_certainty),
        days=len(in_period),
    )
