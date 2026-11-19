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
    Impact,
    PainLocation,
    PainLog,
    Period,
    Severity,
    SleepLog,
    SymptomLog,
    build_brief,
    export_csv,
    evaluate,
    pain_plan,
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

        command = text.strip().upper()
        helped = user.pending.get("helped")
        if helped and "pain" not in user.pending:
            if self._handle_helped(user, helped, text, command):
                return
        if command == "PLAN":
            self._send_plan(user)
            return self._ask_helped(user, "plan")
        if command in ("WRONG", "GALAT"):
            return self._prediction_wrong(user)
        if command == "EXPORT":
            return self._export(user)
        if command == "PROMISE":
            self.messenger.send_text(user.wa_id, t("promise", user.language))
            return
        if command == "DISCREET":
            user.discreet = not user.discreet
            self.store.save(user)
            self.messenger.send_text(user.wa_id, t("discreet_on" if user.discreet else "discreet_off", user.language))
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
                self._ask_helped(user, "brief")
            case "greeting" | "help":
                self.messenger.send_text(user.wa_id, t("welcome", user.language))
            case "off_topic":
                self.messenger.send_text(user.wa_id, t("off_topic", user.language))
            case _:
                self.messenger.send_text(user.wa_id, t("not_understood", user.language))
        if ex.intent in ("log", "status", "greeting", "help"):
            self._maybe_nudge(user)

    # ---- feedback, irregular cycles, export ----------------------------------------
    def _ask_helped(self, user: User, kind: str) -> None:
        """One question after PLAN/BRIEF. The answer is one digit, so it works on any phone, in any language."""
        user.pending["helped"] = {"kind": kind}
        self.store.save(user)
        self.messenger.send_text(user.wa_id, t("helped_q", user.language))

    def _handle_helped(self, user: User, helped: dict, text: str, command: str) -> bool:
        """Returns True if the message was an answer (or free-text reason) and has been consumed."""
        if "why" in helped:  # she said "no" earlier; this message is the reason, in her own words
            user.feedback[-1]["why"] = text.strip()[:200]
            user.pending.pop("helped")
            self.store.save(user)
            self.messenger.send_text(user.wa_id, t("helped_thanks", user.language))
            return True
        answer = {"1": "yes", "2": "a_bit", "3": "no"}.get(command)
        if answer is None:
            user.pending.pop("helped")  # she moved on; don't hold the question open
            self.store.save(user)
            return False
        user.feedback.append({"kind": helped["kind"], "answer": answer, "day": self._today().isoformat()})
        if answer == "no":
            user.pending["helped"] = {"kind": helped["kind"], "why": True}
            self.store.save(user)
            self.messenger.send_text(user.wa_id, t("helped_why", user.language))
        else:
            user.pending.pop("helped")
            self.store.save(user)
            self.messenger.send_text(user.wa_id, t("helped_thanks", user.language))
        return True

    def _prediction_wrong(self, user: User) -> None:
        pred = predict_next_period(user.record)
        if pred is None:
            self.messenger.send_text(user.wa_id, t("status_unknown", user.language))
            return
        user.record.prediction_misses += 1
        user.feedback.append({"kind": "prediction", "answer": "wrong", "day": self._today().isoformat()})
        self.store.save(user)
        self._status(user, prefix=t("wrong_ack", user.language))

    def _export(self, user: User) -> None:
        csv_text = export_csv(user.record)
        self.messenger.send_text(user.wa_id, t("export_head", user.language))
        chunk, size = [], 0
        for line in csv_text.splitlines():
            if size + len(line) > 3500:  # WhatsApp text limit is 4096
                self.messenger.send_text(user.wa_id, "\n".join(chunk))
                chunk, size = [], 0
            chunk.append(line)
            size += len(line) + 1
        self.messenger.send_text(user.wa_id, "\n".join(chunk))
        self.messenger.send_text(user.wa_id, t("export_foot", user.language))

    # ---- pain plan and pre-period heads-up --------------------------------------
    def _send_plan(self, user: User) -> None:
        plan = pain_plan(user.record, self._today())
        basis = t("line_basis_personal" if plan.line.source == "personal" else "line_basis_default", user.language)
        parts = [t("plan_head", user.language, line=plan.line.score, basis=basis), t("plan_steps", user.language)]
        if plan.repeats:
            parts.append(t("plan_doctor", user.language))
        self.messenger.send_text(user.wa_id, "".join(parts))

    def _maybe_nudge(self, user: User) -> None:
        """One heads-up per predicted period, sent alongside a normal reply (so no template is needed).
        Discreet mode swaps the content for a neutral reminder; she reads it with PLAN."""
        plan = pain_plan(user.record, self._today())
        pred = predict_next_period(user.record)
        if not plan.nudge_due or pred is None or user.nudged_for == pred.likely.isoformat():
            return
        user.nudged_for = pred.likely.isoformat()
        self.store.save(user)
        key = "nudge_discreet" if user.discreet else "nudge_intro"
        self.messenger.send_text(user.wa_id, t(key, user.language, days=max(plan.days_to_expected or 0, 0)))

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

        if ex.sleep_hours is not None:
            rec.sleep = [s for s in rec.sleep if s.day != today] + [SleepLog(today, ex.sleep_hours)]
            parts.append(t("sleep_hours", lang, hours=f"{ex.sleep_hours:g}"))

        if ex.pain_mentioned or ex.fever or ex.fainted_or_dizzy:
            pain = {
                "locations": sorted(ex.pain_locations),
                "fever": ex.fever,
                "fainted_or_dizzy": ex.fainted_or_dizzy,
                "duration_minutes": ex.pain_duration_minutes,
                "nausea_vomiting": ex.nausea_vomiting,
                "impacts": sorted(ex.pain_impacts),
            }
            parts += self._pain_detail_labels(pain, lang)
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
    def _pain_detail_labels(pain: dict, lang: str | None) -> list[str]:
        """Read-back text for the extra pain details, so extraction mistakes get caught."""
        labels = []
        if pain.get("duration_minutes") is not None:
            labels.append(t("pain_duration", lang, minutes=pain["duration_minutes"]))
        if pain.get("nausea_vomiting"):
            labels.append(t("nausea", lang))
        labels += [t({"work": "missed_work", "school": "missed_school", "sleep": "poor_sleep"}[i], lang) for i in pain.get("impacts", [])]
        return labels

    @staticmethod
    def _add_pain(rec, day: date, score: int, pain: dict) -> None:
        rec.pain.append(
            PainLog(
                day=day,
                score=score,
                locations={PainLocation(loc) for loc in pain["locations"]},
                fever=pain["fever"],
                fainted_or_dizzy=pain["fainted_or_dizzy"],
                duration_minutes=pain.get("duration_minutes"),
                nausea_vomiting=pain.get("nausea_vomiting", False),
                impacts={Impact(i) for i in pain.get("impacts", [])},
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

    def _status(self, user: User, prefix: str = "") -> None:
        pred = predict_next_period(user.record)
        today = self._today()
        if pred is None:
            self.messenger.send_text(user.wa_id, t("status_unknown", user.language))
            return
        fmt = lambda d: d.strftime("%d %b")  # noqa: E731
        text = prefix + t("status", user.language, cycle_day=user.record.cycle_day(today), likely=fmt(pred.likely),
                          earliest=fmt(pred.earliest), latest=fmt(pred.latest))
        if pred.irregular:
            text += t("irregular_note", user.language)
        self.messenger.send_text(user.wa_id, text)
