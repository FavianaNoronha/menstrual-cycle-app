"""Turn a free-text or transcribed log into structured fields.

Two layers:
1. RuleExtractor (this file): a seed lexicon in English, Hinglish and the four
   launch languages. Fast, free, testable; handles common phrases.
2. An LLM extractor (to add): same `Extraction` output, constrained to the JSON
   schema below, used when rules find nothing. Its output is always read back
   to the user for confirmation before saving.

The lexicon is a starting point. Expand it with native speakers and real
(consented, anonymised) messages from the pilot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# JSON schema the LLM extractor must follow (kept here so both layers agree).
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"enum": ["log", "status", "pain_help", "brief", "delete", "greeting", "help", "off_topic", "unknown"]},
        "period_started": {"type": "boolean"},
        "period_ended": {"type": "boolean"},
        "flow": {"enum": ["light", "medium", "heavy", None]},
        "pain_mentioned": {"type": "boolean"},
        "pain_score": {"type": ["integer", "null"], "minimum": 0, "maximum": 10},
        "pain_locations": {"type": "array", "items": {"type": "string"}},
        "craving_types": {"type": "array", "items": {"type": "string"}},
        "symptoms": {"type": "object", "additionalProperties": {"type": "integer", "minimum": 1, "maximum": 6}},
        "fever": {"type": "boolean"},
        "fainted_or_dizzy": {"type": "boolean"},
        "soaking_hourly": {"type": "boolean"},
    },
    "required": ["intent"],
}


@dataclass
class Extraction:
    intent: str = "unknown"
    period_started: bool = False
    period_ended: bool = False
    flow: str | None = None
    pain_mentioned: bool = False
    pain_score: int | None = None
    pain_locations: set[str] = field(default_factory=set)
    cravings: bool = False
    craving_types: set[str] = field(default_factory=set)
    symptoms: dict[str, int] = field(default_factory=dict)
    fever: bool = False
    fainted_or_dizzy: bool = False
    soaking_hourly: bool = False
    wants_pain_help: bool = False

    def has_log_content(self) -> bool:
        return any(
            [
                self.period_started,
                self.period_ended,
                self.flow,
                self.pain_mentioned,
                self.cravings,
                self.symptoms,
                self.fever,
                self.fainted_or_dizzy,
                self.soaking_hourly,
            ]
        )


# Romanised words are matched on word boundaries; native-script phrases as substrings.
LEXICON: dict[str, list[str]] = {
    "period_started": [
        "period started", "periods started", "got my period", "period came", "periods came", "period aaya",
        "period aa gaya", "periods shuru", "period shuru", "mahwari shuru",
        "पीरियड शुरू", "पीरियड आ गया", "माहवारी शुरू",
        "ಮುಟ್ಟು ಶುರು", "ಮುಟ್ಟು ಆಯಿತು", "ಪೀರಿಯಡ್ ಶುರು",
        "పీరియడ్ వచ్చింది", "నెలసరి వచ్చింది", "పీరియడ్ మొదలైంది",
        "மாதவிடாய் வந்தது", "பீரியட் வந்தது", "மாதவிடாய் தொடங்கியது",
    ],
    "period_ended": [
        "period ended", "period over", "periods over", "period finished", "period khatam", "periods khatam",
        "पीरियड खत्म", "पीरियड ख़त्म", "ಮುಟ್ಟು ಮುಗಿಯಿತು", "ಮುಟ್ಟು ಮುಗಿದಿದೆ",
        "పీరియడ్ అయిపోయింది", "నెలసరి అయిపోయింది", "மாதவிடாய் முடிந்தது", "பீரியட் முடிந்தது",
    ],
    "flow_heavy": ["heavy", "very heavy", "bahut zyada", "bahut jyada", "ज़्यादा", "ज्यादा", "ಹೆಚ್ಚು", "ఎక్కువ", "அதிகம்"],
    "flow_light": ["light", "spotting", "halka", "हल्का", "ಕಡಿಮೆ", "తక్కువ", "குறைவு"],
    "flow_medium": ["medium", "normal flow", "moderate"],
    "pain": [
        "pain", "cramp", "cramps", "ache", "dard", "pet dard", "दर्द", "ऐंठन",
        "ನೋವು", "నొప్పి", "வலி",
    ],
    "loc_lower_back": ["back", "kamar", "कमर", "ಬೆನ್ನು", "నడుము", "முதுகு"],
    "loc_bowel": ["potty", "stool", "motion", "toilet", "bowel"],
    "loc_bladder": ["urine", "peeing", "urination", "पेशाब"],
    "loc_during_sex": ["sex", "intercourse"],
    "loc_one_side": ["one side", "left side", "right side", "ek taraf", "ek side"],
    "craving": ["craving", "cravings", "crave", "want to eat", "khane ka mann", "khane ka man", "खाने का मन", "ಆಸೆ", "కోరిక", "తినాలనిపిస్తోంది", "ஆசை"],
    "c_sweet": ["sweet", "sweets", "meetha", "mithai", "मीठा", "ಸಿಹಿ", "తీపి", "இனிப்பு"],
    "c_chocolate": ["chocolate"],
    "c_salty": ["salty", "namkeen", "chips", "नमकीन"],
    "c_spicy": ["spicy", "teekha", "तीखा", "ಖಾರ", "కారం", "காரம்"],
    "c_fried": ["fried", "samosa", "pakoda", "pakora", "bajji", "vada", "bonda"],
    "mood_low": ["sad", "feeling low", "crying", "cried", "udaas", "उदास", "ಬೇಸರ", "ದುಃಖ", "బాధ", "சோகம்"],
    "irritability": ["irritated", "irritable", "angry", "gussa", "chidchida", "गुस्सा", "चिड़चिड़ा", "ಕೋಪ", "ಕಿರಿಕಿರಿ", "కోపం", "చిరాకు", "கோபம்", "எரிச்சல்"],
    "anxiety": ["anxious", "anxiety", "tension", "worried", "ghabrahat", "घबराहट", "ಆತಂಕ", "ఆందోళన", "பதட்டம்"],
    "mood_swings": ["mood swing", "mood swings", "moody"],
    "energy_low": ["tired", "exhausted", "no energy", "thakan", "thaka", "थकान", "ಸುಸ್ತು", "అలసట", "சோர்வு"],
    "bloating": ["bloated", "bloating", "gas", "pet phoola", "ಹೊಟ್ಟೆ ಉಬ್ಬರ", "ఉబ్బరం", "உப்புசம்"],
    "fever": ["fever", "bukhar", "बुखार", "ಜ್ವರ", "జ్వరం", "காய்ச்சல்"],
    "faint": ["faint", "fainted", "dizzy", "chakkar", "चक्कर", "ತಲೆ ಸುತ್ತು", "కళ్లు తిరుగు", "தலைசுற்றல்", "மயக்கம்"],
    "soaking_hourly": ["every hour", "har ghante", "हर घंटे", "ಪ್ರತಿ ಗಂಟೆ", "ప్రతి గంట", "ஒவ்வொரு மணி"],
    "intensifier": ["very", "bahut", "too much", "बहुत", "ತುಂಬಾ", "చాలా", "மிகவும்", "ரொம்ப"],
}

INTENTS: dict[str, list[str]] = {
    "delete": ["delete", "delete my data"],
    "brief": ["brief", "doctor summary", "report"],
    "status": ["status", "next period", "when is my period", "kab aayega", "kab aaega"],
    "pain_help": ["pain help", "pain relief", "help cramps", "how to reduce pain", "dard kaise kam", "relief"],
    "help": ["help", "menu"],
    "greeting": ["hi", "hello", "hey", "namaste", "namaskara", "vanakkam", "start"],
}

SCORE_RE = re.compile(r"(?<!\d)(10|[0-9])\s*(?:/|out of|by)\s*10\b")
LONE_SCORE_RE = re.compile(r"^\s*(10|[0-9])\s*$")
ROMAN_RE = re.compile(r"^[\x00-\x7f]+$")


def _has(text: str, phrases: list[str]) -> bool:
    for phrase in phrases:
        if ROMAN_RE.match(phrase):
            if re.search(rf"(?<![a-z]){re.escape(phrase)}(?![a-z])", text):
                return True
        elif phrase in text:
            return True
    return False


class RuleExtractor:
    def extract(self, raw: str) -> Extraction:
        text = raw.strip().lower()
        ex = Extraction()
        if not text:
            return ex

        stripped = text.strip(" !.?")
        for intent, phrases in INTENTS.items():
            if stripped in phrases:
                ex.intent = intent
                return ex
        ex.wants_pain_help = _has(text, INTENTS["pain_help"])
        if _has(text, ["next period", "kab aayega", "when is my period"]):
            ex.intent = "status"
            return ex

        ex.period_started = _has(text, LEXICON["period_started"])
        ex.period_ended = _has(text, LEXICON["period_ended"])
        if _has(text, LEXICON["flow_heavy"]):
            ex.flow = "heavy"
        elif _has(text, LEXICON["flow_medium"]):
            ex.flow = "medium"
        elif _has(text, LEXICON["flow_light"]):
            ex.flow = "light"

        if _has(text, LEXICON["pain"]):
            ex.pain_mentioned = True
        if m := SCORE_RE.search(text):
            ex.pain_mentioned = True
            ex.pain_score = int(m.group(1))
        for loc in ("lower_back", "bowel", "bladder", "during_sex", "one_side"):
            if _has(text, LEXICON[f"loc_{loc}"]):
                ex.pain_locations.add(loc)
        if ex.pain_locations - {"lower_back"}:
            ex.pain_mentioned = True

        types = {k[2:] for k in LEXICON if k.startswith("c_") and _has(text, LEXICON[k])}
        if _has(text, LEXICON["craving"]) or types:
            ex.cravings = True
            ex.craving_types = types
            ex.symptoms["cravings"] = 4

        rating = 5 if _has(text, LEXICON["intensifier"]) else 4
        for item in ("mood_low", "irritability", "anxiety", "mood_swings", "energy_low", "bloating"):
            if _has(text, LEXICON[item]):
                ex.symptoms[item] = rating
        if "cravings" in ex.symptoms and rating == 5:
            ex.symptoms["cravings"] = 5

        ex.fever = _has(text, LEXICON["fever"])
        ex.fainted_or_dizzy = _has(text, LEXICON["faint"])
        ex.soaking_hourly = _has(text, LEXICON["soaking_hourly"])

        if ex.has_log_content():
            ex.intent = "log"
        elif ex.wants_pain_help:
            ex.intent = "pain_help"
        elif _has(text, INTENTS["greeting"]):
            ex.intent = "greeting"
        elif len(text.split()) >= 4:
            ex.intent = "off_topic"
        return ex

    @staticmethod
    def lone_score(raw: str) -> int | None:
        m = LONE_SCORE_RE.match(raw)
        return int(m.group(1)) if m else None
