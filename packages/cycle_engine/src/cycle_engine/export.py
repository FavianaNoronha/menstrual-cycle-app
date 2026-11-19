"""Her data, back to her, in a format any spreadsheet opens. No lock-in, no paywall.

Plain CSV text: type,date,value,notes. Small enough to send as WhatsApp text and
to paste into Excel/Sheets. Nothing here is derived or interpreted, only what she logged.
"""

from __future__ import annotations

import csv
import io

from .models import CycleRecord


def export_csv(record: CycleRecord) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["type", "date", "value", "notes"])
    for p in record.sorted_periods():
        w.writerow(["period_start", p.start.isoformat(), "", ""])
        if p.end:
            w.writerow(["period_end", p.end.isoformat(), "", ""])
    for f in sorted(record.flow, key=lambda x: x.day):
        w.writerow(["flow", f.day.isoformat(), getattr(f.level, "value", f.level), ""])
    for x in sorted(record.pain, key=lambda x: x.day):
        notes = ";".join(sorted([l.value for l in x.locations] + [i.value for i in x.impacts]))
        w.writerow(["pain", x.day.isoformat(), x.score, notes])
    for sy in sorted(record.symptoms, key=lambda x: x.day):
        for name, rating in sorted(sy.ratings.items()):
            w.writerow(["symptom", sy.day.isoformat(), rating, name])
    for sl in sorted(record.sleep, key=lambda x: x.day):
        w.writerow(["sleep_hours", sl.day.isoformat(), sl.hours, ""])
    return out.getvalue()
