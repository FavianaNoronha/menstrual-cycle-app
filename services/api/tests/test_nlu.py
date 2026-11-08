import pytest

from app.nlu import RuleExtractor

ex = RuleExtractor()


@pytest.mark.parametrize(
    "text",
    [
        "period started today",
        "aaj period aa gaya",
        "आज पीरियड शुरू हुआ",
        "ಇಂದು ಮುಟ್ಟು ಶುರು",
        "ఈ రోజు పీరియడ్ వచ్చింది",
        "இன்று மாதவிடாய் வந்தது",
    ],
)
def test_period_start_in_five_languages(text):
    out = ex.extract(text)
    assert out.intent == "log"
    assert out.period_started


def test_full_english_log():
    out = ex.extract("Period started, very heavy, cramps 7/10, craving sweets and chips, so irritated")
    assert out.period_started and out.flow == "heavy"
    assert out.pain_score == 7
    assert out.craving_types == {"sweet", "salty"}
    assert out.symptoms["irritability"] == 5  # "very" bumps the rating
    assert out.symptoms["cravings"] == 5


def test_hinglish_pain_without_score_and_back():
    out = ex.extract("bahut pet dard hai, kamar bhi")
    assert out.pain_mentioned and out.pain_score is None
    assert "lower_back" in out.pain_locations


def test_native_script_symptoms():
    assert "irritability" in ex.extract("ತುಂಬಾ ಕೋಪ ಬರುತ್ತಿದೆ").symptoms
    assert ex.extract("తీపి తినాలనిపిస్తోంది").craving_types == {"sweet"}
    assert ex.extract("ரொம்ப சோர்வு").symptoms == {"energy_low": 5}


def test_word_boundaries_avoid_false_matches():
    out = ex.extract("my flow is normal")
    assert "mood_low" not in out.symptoms


def test_red_flag_words():
    out = ex.extract("heavy bleeding, changing pad every hour, feeling dizzy")
    assert out.soaking_hourly and out.fainted_or_dizzy


def test_intents():
    assert ex.extract("status").intent == "status"
    assert ex.extract("DELETE").intent == "delete"
    assert ex.extract("pain relief?").intent == "pain_help"
    assert ex.extract("hello").intent == "greeting"
    assert ex.extract("who won the cricket match yesterday").intent == "off_topic"


def test_log_plus_help_keeps_the_log():
    out = ex.extract("cramps 8/10 need pain relief")
    assert out.intent == "log" and out.pain_score == 8 and out.wants_pain_help


def test_lone_score():
    assert RuleExtractor.lone_score(" 6 ") == 6
    assert RuleExtractor.lone_score("6 days") is None


def test_pain_details_are_extracted_in_english():
    r = ex.extract("cramps 8/10 for 3 hours, vomited and missed work, couldn't sleep")
    assert r.pain_score == 8 and r.pain_duration_minutes == 180
    assert r.nausea_vomiting and r.pain_impacts == {"work", "sleep"}


def test_minutes_and_all_day():
    assert ex.extract("pain 45 minutes").pain_duration_minutes == 45
    assert ex.extract("pain all day").pain_duration_minutes == 1440


def test_hinglish_and_native_details():
    r = ex.extract("pet dard bahut, ulti hui, office nahi gaya")
    assert r.pain_mentioned and r.nausea_vomiting and "work" in r.pain_impacts
    assert ex.extract("வலி, வாந்தி").nausea_vomiting
    assert "school" in ex.extract("दर्द था, स्कूल नहीं गई").pain_impacts


def test_sleep_hours_are_not_mistaken_for_pain_duration():
    r = ex.extract("slept 5 hours, mild cramps")
    assert r.sleep_hours == 5.0 and r.pain_duration_minutes is None
    assert ex.extract("slept only 6.5 hrs").sleep_hours == 6.5


def test_details_ignored_without_pain():
    r = ex.extract("I vomited at work, feeling tired")
    assert not r.nausea_vomiting and not r.pain_impacts
