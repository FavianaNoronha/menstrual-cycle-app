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
        "pain_duration_minutes": {"type": ["integer", "null"], "minimum": 0},
        "nausea_vomiting": {"type": "boolean"},
        "pain_impacts": {"type": "array", "items": {"enum": ["work", "school", "sleep"]}},
        "sleep_hours": {"type": ["number", "null"], "minimum": 0, "maximum": 24},
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
    pain_duration_minutes: int | None = None
    nausea_vomiting: bool = False
    pain_impacts: set[str] = field(default_factory=set)  # subset of {"work", "school", "sleep"}
    sleep_hours: float | None = None

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
                self.sleep_hours is not None,
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
        # Everyday and coded words. UNVERIFIED: each needs a native speaker's OK (docs/product/period-words.md).
        # Bare "mc"/"dates"/"dooram" are ambiguous, so only first-person phrases with a verb are listed.
        "mc aayi", "mc aa gayi", "mc start", "mc started", "mc shuru", "my mc started", "got my mc",
        "chums", "aunt flo", "aunt flo is here", "that time of the month", "tom started", "my dates started",
        "dates aa gayi", "dates aaye", "dates start",
        "mahina aa gaya", "mahina shuru", "mera mahina aa gaya", "kapde aaye", "kapde aa gaye",
        "महीना आ गया", "महीना शुरू", "मेरा महीना आ गया", "कपड़े आ गए", "मासिक शुरू", "मासिक धर्म शुरू", "डेट्स आ गई",
        "డేట్స్ వచ్చాయి", "నేను దూరం",
        "டேட்ஸ் வந்தது", "நான் தூரம்", "வீட்டுக்கு தூரம்",
    ],
    "period_ended": [
        "period ended", "period over", "periods over", "period finished", "period khatam", "periods khatam",
        "mc khatam", "mc over", "mc ho gayi khatam", "chums over", "dates khatam",
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
    "nausea": ["nausea", "nauseous", "vomit", "vomited", "vomiting", "threw up", "feel sick", "ulti", "उल्टी", "मतली", "ವಾಂತಿ", "ವಾಕರಿಕೆ", "వాంతి", "వికారం", "வாந்தி", "குமட்டல்"],
    "impact_work": ["missed work", "couldn't work", "could not work", "can't work", "cant work", "off from work", "office nahi", "काम नहीं कर", "ಕೆಲಸಕ್ಕೆ ಹೋಗಲಿಲ್ಲ", "పనికి వెళ్లలేదు", "வேலைக்கு போகவில்லை"],
    "impact_school": ["missed school", "missed class", "missed college", "school nahi", "college nahi", "स्कूल नहीं", "कॉलेज नहीं", "ಶಾಲೆಗೆ ಹೋಗಲಿಲ್ಲ", "ಕಾಲೇಜಿಗೆ ಹೋಗಲಿಲ್ಲ", "స్కూల్‌కి వెళ్లలేదు", "కాలేజీకి వెళ్లలేదు", "பள்ளிக்கு போகவில்லை", "கல்லூரிக்கு போகவில்லை"],
    "impact_sleep": ["couldn't sleep", "could not sleep", "can't sleep", "cant sleep", "no sleep", "woke up with pain", "neend nahi", "नींद नहीं", "ನಿದ್ರೆ ಬರಲಿಲ್ಲ", "నిద్ర పట్టలేదు", "தூக்கம் வரவில்லை"],
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
SLEEP_RE = re.compile(r"\bslept\s+(?:only\s+|just\s+|about\s+)?(\d{1,2}(?:\.\d)?)\s*(?:hours?|hrs?|h)\b")
DURATION_HOURS_RE = re.compile(r"(?<!slept )(?<!slept only )(?<!\d)(\d{1,2}(?:\.\d)?)\s*(?:hours?|hrs?|h)\b")
DURATION_MIN_RE = re.compile(r"(?<!\d)(\d{1,3})\s*(?:minutes?|mins?)\b")
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

        if m := SLEEP_RE.search(text):
            hours = float(m.group(1))
            if 0 <= hours <= 24:
                ex.sleep_hours = hours
        # Details below only mean something attached to a pain entry.
        if ex.pain_mentioned:
            ex.nausea_vomiting = _has(text, LEXICON["nausea"])
            for kind in ("work", "school", "sleep"):
                if _has(text, LEXICON[f"impact_{kind}"]):
                    ex.pain_impacts.add(kind)
            if m := DURATION_MIN_RE.search(text):
                ex.pain_duration_minutes = int(m.group(1))
            elif (m := DURATION_HOURS_RE.search(text)) and SLEEP_RE.search(text) is None:
                ex.pain_duration_minutes = int(float(m.group(1)) * 60)
            elif _has(text, ["all day", "whole day", "din bhar", "दिन भर"]):
                ex.pain_duration_minutes = 24 * 60

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
