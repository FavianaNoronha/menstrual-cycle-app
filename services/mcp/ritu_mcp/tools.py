"""Pure functions behind the MCP tools. They only see one user's record.

Design rules:
- Return summaries, not raw daily logs (data minimisation).
- Every response carries `not_a_diagnosis: True` and, when relevant, the
  red-flag guidance verbatim from the engine, so an assistant can't soften it.
"""

from __future__ import annotations

from datetime import date, timedelta
from statistics import median

from ritu_engine import (
    CycleRecord,
    Severity,
    analyze_cyclicity,
    build_brief,
    estimate_phase,
    evaluate,
    predict_next_period,
    score_period,
    top_cravings,
)

SEVERITY_GUIDANCE = {
    Severity.URGENT: "Seek medical care today. In India call 112 (emergency) or 108 (ambulance).",
    Severity.SOON: "Book a doctor visit in the coming weeks.",
    Severity.DISCUSS: "Mention at the next doctor visit.",
    Severity.INFO: "For awareness.",
}


def cycle_status(record: CycleRecord, today: date) -> dict:
    pred = predict_next_period(record)
    return {
        "cycle_day": record.cycle_day(today),
        "phase_estimate": estimate_phase(record, today).value,
        "next_period": None
        if pred is None
        else {
            "earliest": pred.earliest.isoformat(),
            "likely": pred.likely.isoformat(),
            "latest": pred.latest.isoformat(),
            "confidence": pred.confidence.value,
        },
        "note": "Phase is a calendar estimate; it is unreliable for irregular cycles or without ovulation.",
        "not_a_diagnosis": True,
    }


def trends(record: CycleRecord, today: date, months: int = 6) -> dict:
    since = today - timedelta(days=30 * max(1, min(months, 24)))
    periods = [p for p in record.sorted_periods() if p.start >= since]
    starts = [p.start for p in periods]
    lengths = [(b - a).days for a, b in zip(starts, starts[1:])]
    flow = [score_period(record.flow, p.start, p.end).pbac for p in periods if p.end is not None]
    pain_peaks = []
    for p in periods:
        end = p.end or p.start + timedelta(days=6)
        scores = [l.score for l in record.pain if p.start - timedelta(days=2) <= l.day <= end]
        if scores:
            pain_peaks.append(max(scores))
    patterns = [
        {"symptom": p.item, "rises_before_period_in": f"{p.cycles_cyclical}/{p.cycles_analyzed} cycles"}
        for p in analyze_cyclicity(record)
        if p.consistent
    ]
    return {
        "months": months,
        "cycle_lengths_days": lengths,
        "cycle_length_median": median(lengths) if lengths else None,
        "flow_pbac_by_period": flow,
        "flow_note": "PBAC > 100 suggests heavy bleeding.",
        "peak_pain_by_period": pain_peaks,
        "premenstrual_patterns": patterns,
        "premenstrual_cravings": top_cravings(record),
        "not_a_diagnosis": True,
    }


def flags(record: CycleRecord, today: date) -> dict:
    return {
        "flags": [
            {"code": f.code, "severity": f.severity.value, "guidance": SEVERITY_GUIDANCE[f.severity], "evidence": f.evidence}
            for f in evaluate(record, today)
        ],
        "instruction_for_assistant": "Relay urgent and soon guidance as written. Do not diagnose or reassure them away.",
        "not_a_diagnosis": True,
    }


def doctor_brief(record: CycleRecord, today: date) -> dict:
    return build_brief(record, today)
