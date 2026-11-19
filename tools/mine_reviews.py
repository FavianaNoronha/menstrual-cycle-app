#!/usr/bin/env python3
"""Count what people complain about in exported app-store reviews.

Usage: python tools/mine_reviews.py reviews.csv [--examples N] [--max-rating R]
CSV needs a header with at least `text`; `rating` and `app` are used when present.
Keyword themes, not a model: rough counts, read the examples. Local only, no network.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict

THEMES: dict[str, list[str]] = {
    "paywall": ["premium", "paywall", "subscription", "subscribe", "pay to", "paid", "price", "expensive", "free trial", "charged", "refund", "paise", "paisa"],
    "privacy": ["privacy", "private", "personal data", "data shar", "sell my", "sell", "sold", "share my", "tracking me", "ads", "advertis", "leak", "safe", "surveillance", "police", "court"],
    "prediction wrong": ["inaccurate", "wrong date", "not accurate", "accuracy", "prediction", "predict", "late", "early", "irregular", "pcos", "pcod", "never right", "galat", "sahi nahi"],
    "lost data": ["lost my data", "lost all", "data gone", "deleted my", "backup", "restore", "reinstall", "disappeared", "erased", "sync"],
    "language": ["hindi", "tamil", "telugu", "kannada", "marathi", "bengali", "language", "english only", "translate", "regional"],
    "notifications / embarrassing": ["notification", "embarrass", "pink", "shared phone", "family", "mother", "husband", "parents", "someone saw", "discreet", "icon"],
    "ads / spam": ["too many ads", "ad every", "popup", "pop-up", "spam", "ads everywhere", "advert"],
    "bugs / crashes": ["crash", "bug", "glitch", "freeze", "not opening", "slow", "won't load", "login", "log in", "otp", "update broke"],
    "pain / symptoms missing": ["pain", "cramp", "mood", "symptom", "pms", "cravings", "doctor", "advice", "what to do"],
    "not for my situation": ["pregnan", "ttc", "conceive", "menopaus", "perimenopause", "teen", "unmarried", "single", "not married", "no sex"],
}


def load(path: str, max_rating: float | None):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or "text" not in rows[0]:
        sys.exit("CSV needs a header row with a `text` column (and optionally `rating`, `app`).")
    out = []
    for r in rows:
        text = (r.get("text") or "").strip()
        if not text:
            continue
        try:
            rating = float(r.get("rating", ""))
        except ValueError:
            rating = None
        if max_rating is not None and rating is not None and rating > max_rating:
            continue
        out.append({"app": r.get("app") or "?", "rating": rating, "text": text})
    return out


def tag(text: str) -> list[str]:
    low = text.lower()
    return [name for name, words in THEMES.items() if any(re.search(r"\b" + re.escape(w), low) for w in words)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv")
    ap.add_argument("--examples", type=int, default=2)
    ap.add_argument("--max-rating", type=float, default=3.0, help="only reviews at or below this rating (default 3)")
    args = ap.parse_args()

    reviews = load(args.csv, args.max_rating)
    if not reviews:
        sys.exit("No reviews left after filtering.")
    counts: Counter[str] = Counter()
    by_app: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, list[str]] = defaultdict(list)
    untagged = 0
    for r in reviews:
        themes = tag(r["text"])
        if not themes:
            untagged += 1
        for th in themes:
            counts[th] += 1
            by_app[r["app"]][th] += 1
            if len(examples[th]) < args.examples:
                examples[th].append(r["text"][:200].replace("\n", " "))

    n = len(reviews)
    print(f"{n} reviews (rating <= {args.max_rating}); {untagged} matched no theme\n")
    for th, c in counts.most_common():
        print(f"{th:32s} {c:5d}  ({100 * c / n:.0f}%)")
        for ex in examples[th]:
            print(f"    - {ex}")
    if len(by_app) > 1:
        print("\nBy app (top 3 themes each):")
        for app, cnt in sorted(by_app.items()):
            print(f"  {app}: " + ", ".join(f"{k} {v}" for k, v in cnt.most_common(3)))
    print("\nCounts are keyword matches; one review can hit several themes. Read the examples.")


if __name__ == "__main__":
    main()
