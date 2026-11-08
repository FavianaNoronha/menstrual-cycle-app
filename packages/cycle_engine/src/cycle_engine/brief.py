"""The one-page doctor brief: what she shows her gynaecologist.

Structured data first (for PDF, FHIR export and the MCP connector), then a
plain-text rendering. Clinician-facing text stays in English for now; the
user-facing explanation of each section is localised in the app.
"""

from __future__ import annotations

from datetime import date
from statistics import median

from .models import CycleRecord
from .norms import Severity
from .pain import pain_summary
from .pbac import score_period
from .prediction import predict_next_period
from .red_flags import evaluate
from .symptoms import CORE_ITEMS, analyze_cyclicity, top_cravings

QUESTIONS = {
    "cycles_irregular": "My cycles vary a lot. Should we check thyroid, prolactin or PCOS?",
    "cycles_infrequent": "My cycles are often longer than 38 days. What could cause this?",
    "cycles_frequent": "My cycles are often shorter than 24 days. Is that a concern?",
    "bleeding_prolonged": "My periods last more than 8 days. What should we check?",
    "heavy_bleeding_pattern": "My flow scores suggest heavy bleeding. Should I get an Hb / iron test?",
    "painkillers_not_helping": "Painkillers don't help my period pain. What are the next options?",
    "pain_pattern_bowel_bladder_sex": "I get pain with bowel movements, urination or sex around periods. Could this be endometriosis?",
    "pain_outside_periods": "I have pelvic pain outside my periods. What could cause it?",
    "pain_disrupting_daily_life": "My period pain stops me from working, studying or sleeping. What are the next options?",
    "pain_worsening": "My period pain is getting worse each cycle. Should we investigate?",
    "no_period_90_days": "I haven't had a period in over 3 months. What should we test?",
    "transition_early_signs": "Could these cycle changes be early perimenopause?",
    "transition_late_signs": "I'm having long gaps between periods. Is this perimenopause?",
}


def build_brief(record: CycleRecord, today: date) -> dict:
    periods = record.sorted_periods()
    lengths = record.cycle_lengths()
    durations = [p.length_days() for p in periods if p.length_days() is not None]
    flow = [
        {"start": p.start.isoformat(), **score_period(record.flow, p.start, p.end).__dict__}
        for p in periods[-6:]
        if p.end is not None
    ]
    findings = evaluate(record, today)
    patterns = [
        {"item": p.item, "label": CORE_ITEMS.get(p.item, p.item), "cycles": p.cycles_analyzed, "cyclical_in": p.cycles_cyclical}
        for p in analyze_cyclicity(record)
        if p.consistent
    ]
    pred = predict_next_period(record)
    return {
        "generated_on": today.isoformat(),
        "period_from": periods[0].start.isoformat() if periods else None,
        "cycles_logged": len(lengths),
        "cycle_lengths_recent": lengths[-6:],
        "cycle_length_median": median(lengths) if lengths else None,
        "cycle_variation_days": (max(lengths[-6:]) - min(lengths[-6:])) if len(lengths) >= 2 else None,
        "bleeding_days_recent": durations[-6:],
        "flow_scores": flow,
        "pain": pain_summary(record),
        "premenstrual_patterns": patterns,
        "premenstrual_cravings": top_cravings(record),
        "next_period": None
        if pred is None
        else {"earliest": pred.earliest.isoformat(), "likely": pred.likely.isoformat(), "latest": pred.latest.isoformat()},
        "findings": [{"code": f.code, "severity": f.severity.value, "evidence": f.evidence} for f in findings],
        "questions_to_ask": [QUESTIONS[f.code] for f in findings if f.code in QUESTIONS],
        "disclaimer": "Self-reported data summarised by Cycle Companion. Not a diagnosis.",
    }


def render_text(brief: dict) -> str:
    lines = [
        "CYCLE SUMMARY (self-reported, not a diagnosis)",
        f"Generated {brief['generated_on']} | records from {brief['period_from'] or '-'}",
        "",
        f"Cycles logged: {brief['cycles_logged']}",
        f"Recent cycle lengths (days): {brief['cycle_lengths_recent'] or '-'}  median {brief['cycle_length_median'] or '-'}",
        f"Variation (shortest to longest, days): {brief['cycle_variation_days'] if brief['cycle_variation_days'] is not None else '-'}",
        f"Bleeding days per period: {brief['bleeding_days_recent'] or '-'}",
    ]
    if brief["flow_scores"]:
        lines.append("Flow (PBAC; >100 = heavy): " + ", ".join(str(f["pbac"]) for f in brief["flow_scores"]))
    pain = brief["pain"]
    if pain["cycles_with_pain_logs"]:
        lines.append(f"Peak pain by cycle (0-10): {pain['peak_pain_by_cycle']}")
        t = pain["pain_days_by_timing"]
        lines.append(f"Pain days: {t['before']} before periods, {t['during']} during, {t['outside']} outside periods")
        if pain["typical_duration_minutes"] is not None:
            lines.append(f"Typical pain duration: {pain['typical_duration_minutes']} minutes")
        if pain["nausea_or_vomiting_rate"]:
            lines.append(f"Nausea or vomiting with pain on {int(pain['nausea_or_vomiting_rate'] * 100)}% of pain days")
        if pain["days_activity_missed"]:
            lines.append("Pain stopped her: " + ", ".join(f"{k} ({v} days)" for k, v in pain["days_activity_missed"].items()))
        for tr in pain["treatments"]:
            if tr["status"] == "ok":
                lines.append(
                    f"{tr['treatment']} (started {tr['started']}): average peak pain {tr['average_peak_before']} -> "
                    f"{tr['average_peak_after']} (observed, not proof of cause)"
                )
            else:
                lines.append(f"{tr['treatment']} (started {tr['started']}): not enough cycles logged yet to compare")
        if pain["painkiller_helped_rate"] is not None:
            lines.append(f"Painkiller helped: {int(pain['painkiller_helped_rate'] * 100)}% of times taken")
    if brief["premenstrual_patterns"]:
        lines.append("Symptoms that rise before periods: " + ", ".join(p["label"] for p in brief["premenstrual_patterns"]))
    if brief["premenstrual_cravings"]:
        lines.append("Premenstrual cravings: " + ", ".join(brief["premenstrual_cravings"]))
    flags = [f for f in brief["findings"] if f["severity"] != Severity.INFO.value]
    if flags:
        lines += ["", "Flags:"] + [f"- [{f['severity']}] {f['code']}" for f in flags]
    if brief["questions_to_ask"]:
        lines += ["", "Questions to ask:"] + [f"- {q}" for q in brief["questions_to_ask"]]
    return "\n".join(lines)
