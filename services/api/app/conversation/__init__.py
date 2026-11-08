"""The WhatsApp conversation: language -> consent -> logging, status, pain help, brief, delete.

Rules that keep us safe and policy-compliant:
- Nothing health-related is stored before explicit consent (DPDP).
- Every save is read back to the user ("Saved: ...") so extraction errors get caught.
- Red flags come from cycle_engine.evaluate, never from a language model.
- Off-topic chat gets a scoped refusal (WhatsApp Business AI policy, Jan 2026).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from cycle_engine import (
    FlowLog,
    PainLocation,
    PainLog,
    Period,
    Severity,
    SymptomLog,
    build_brief,
    evaluate,
    predict_next_period,
    render_text,
)

from ..i18n import LANGUAGES, t
from ..nlu import Extraction, RuleExtractor
from ..speech import BCP47_TO_APP, Transcriber
from ..store import Store, User
from ..whatsapp import InboundMessage, Messenger

IST = timezone(timedelta(hours=5, minutes=30))


class ConversationHandler:
    def __init__(self, store: Store, messenger: Messenger, transcriber: Transcriber | None = None,
                 extractor: RuleExtractor | None = None, today: callable = None) -> None:
        self.store = store
        self.messenger = messenger
        self.transcriber = transcriber
        self.extractor = extractor or RuleExtractor()
        self._today = today or (lambda: datetime.now(IST).date())

    # ---- entry point -------------------------------------------------------
    def handle(self, msg: InboundMessage) -> None:
        if self.store.seen_message(msg.message_id):
            return
        user = self.store.get_or_create(msg.wa_id)

        if msg.kind == "button" and msg.reply_id:
            if self._handle_button(user, msg.reply_id):
                return

        text = msg.text
        if msg.kind == "audio":
            text = self._transcribe(user, msg)
            if text is None:
                return

        if user.language is None:
            return self._ask_language(user)
        if user.consented_at is None:
            return self._ask_consent(user)

        if text.strip().upper() == "DELETE":
            self.store.delete(user.wa_id)
            self.messenger.send_text(user.wa_id, t("deleted", user.language))
            return

        if "pain" in user.pending and (score := self.extractor.lone_score(text)) is not None:
            return self._complete_pain(user, score)

        ex = self.extractor.extract(text)
        match ex.intent:
            case "log":
                self._log(user, ex)
                if ex.wants_pain_help:
                    self.messenger.send_text(user.wa_id, t("pain_help", user.language))
            case "status":
                self._status(user)
            case "pain_help":
                self.messenger.send_text(user.wa_id, t("pain_help", user.language))
            case "brief":
                self.messenger.send_text(user.wa_id, render_text(build_brief(user.record, self._today())))
            case "greeting" | "help":
                self.messenger.send_text(user.wa_id, t("welcome", user.language))
            case "off_topic":
                self.messenger.send_text(user.wa_id, t("off_topic", user.language))
            case _:
                self.messenger.send_text(user.wa_id, t("not_understood", user.language))

    # ---- onboarding ----------------------------------------------------------
    def _ask_language(self, user: User) -> None:
        rows = [(f"lang_{code}", name) for code, name in LANGUAGES.items()]
        self.messenger.send_list(user.wa_id, t("choose_language", "en"), "Language / भाषा", rows)

    def _ask_consent(self, user: User) -> None:
        lang = user.language
        self.messenger.send_buttons(
            user.wa_id, t("consent", lang), [("consent_yes", t("yes", lang)), ("consent_no", t("no", lang))]
        )

    def _handle_button(self, user: User, reply_id: str) -> bool:
        if reply_id.startswith("lang_") and reply_id[5:] in LANGUAGES:
            user.language = reply_id[5:]
            self.store.save(user)
            self._ask_consent(user)
            return True
        if reply_id == "consent_yes":
            user.consented_at = datetime.now(timezone.utc)
            self.store.save(user)
            self.messenger.send_text(user.wa_id, t("welcome", user.language))
            return True
        if reply_id == "consent_no":
            lang = user.language
            self.store.delete(user.wa_id)  # keep nothing, not even the language choice
            self.messenger.send_text(user.wa_id, t("consent_declined", lang))
            return True
        return False

    def _transcribe(self, user: User, msg: InboundMessage) -> str | None:
        if self.transcriber is None or msg.media_id is None:
            self.messenger.send_text(user.wa_id, t("not_understood", user.language))
            return None
        audio, mime = self.messenger.download_media(msg.media_id)
        text, lang_code = self.transcriber.transcribe(audio, mime)
        if user.language is None and lang_code in BCP47_TO_APP:
            user.language = BCP47_TO_APP[lang_code]
        return text

    # ---- logging -------------------------------------------------------------
    def _log(self, user: User, ex: Extraction) -> None:
        today = self._today()
        rec = user.record
        parts: list[str] = []
        lang = user.language

        if ex.period_started:
            last = rec.last_period()
            if last is None or (today - last.start).days > 10:
                rec.periods.append(Period(start=today))
            parts.append(t("period_started", lang))
        if ex.period_ended:
            last = rec.last_period()
            if last and last.end is None:
                last.end = today
            parts.append(t("period_ended", lang))
        if ex.flow:
            rec.flow.append(FlowLog(day=today, level=ex.flow))
            parts.append(t(f"flow_{ex.flow}", lang))
            if ex.flow == "heavy" and ex.soaking_hourly:
                rec.soaking_hourly_hours = max(rec.soaking_hourly_hours, 2)
        elif ex.soaking_hourly:
            rec.soaking_hourly_hours = max(rec.soaking_hourly_hours, 2)
        if ex.symptoms:
            rec.symptoms.append(SymptomLog(day=today, ratings=dict(ex.symptoms), craving_types=set(ex.craving_types)))
            parts += [t(item, lang) for item in ex.symptoms if item != "cravings"]
            if ex.cravings:
                kinds = f" ({', '.join(sorted(ex.craving_types))})" if ex.craving_types else ""
                parts.append(t("cravings", lang) + kinds)

        if ex.pain_mentioned or ex.fever or ex.fainted_or_dizzy:
            pain = {
                "locations": sorted(ex.pain_locations),
                "fever": ex.fever,
                "fainted_or_dizzy": ex.fainted_or_dizzy,
            }
            if ex.pain_score is None and ex.pain_mentioned:
                user.pending["pain"] = pain
            else:
                self._add_pain(rec, today, ex.pain_score or 0, pain)
                if ex.pain_score is not None:
                    parts.append(t("pain", lang, score=ex.pain_score))

        self.store.save(user)
        if parts:
            self.messenger.send_text(user.wa_id, t("logged", lang, summary=", ".join(parts)))
        if "pain" in user.pending:
            self.messenger.send_text(user.wa_id, t("ask_pain_score", lang))
        self._check_flags(user)

    def _complete_pain(self, user: User, score: int) -> None:
        pain = user.pending.pop("pain")
        self._add_pain(user.record, self._today(), score, pain)
        self.store.save(user)
        self.messenger.send_text(user.wa_id, t("logged", user.language, summary=t("pain", user.language, score=score)))
        if score >= 7:
            self.messenger.send_text(user.wa_id, t("pain_help", user.language))
        self._check_flags(user)

    @staticmethod
    def _add_pain(rec, day: date, score: int, pain: dict) -> None:
        rec.pain.append(
            PainLog(
                day=day,
                score=score,
                locations={PainLocation(loc) for loc in pain["locations"]},
                fever=pain["fever"],
                fainted_or_dizzy=pain["fainted_or_dizzy"],
            )
        )

    def _check_flags(self, user: User) -> None:
        findings = evaluate(user.record, self._today())
        new_urgent = [f for f in findings if f.severity is Severity.URGENT and f.code not in user.alerted_codes]
        new_soon = [f for f in findings if f.severity is Severity.SOON and f.code not in user.alerted_codes]
        if new_urgent:
            self.messenger.send_text(user.wa_id, t("urgent", user.language))
        elif new_soon:
            self.messenger.send_text(user.wa_id, t("soon", user.language))
        user.alerted_codes.update(f.code for f in new_urgent + new_soon)
        self.store.save(user)

    def _status(self, user: User) -> None:
        pred = predict_next_period(user.record)
        today = self._today()
        if pred is None:
            self.messenger.send_text(user.wa_id, t("status_unknown", user.language))
            return
        fmt = lambda d: d.strftime("%d %b")  # noqa: E731
        self.messenger.send_text(
            user.wa_id,
            t("status", user.language, cycle_day=user.record.cycle_day(today), likely=fmt(pred.likely),
              earliest=fmt(pred.earliest), latest=fmt(pred.latest)),
        )
