# Cycle Companion (codename)

**Cycle health in your language.** An Android app and WhatsApp bot that turn period, flow, pain and mood logs into clinically useful insight — in English, Hindi, Kannada, Telugu and Tamil — plus an MCP connector so Claude, ChatGPT and other assistants can read a woman's cycle summary with her consent.

> Codename only. The brand name is undecided (the first working name was already taken); it is a placeholder string in i18n, the app title and docs. Check the Play Store and the Indian trademark register before choosing.

## What's in this repo

| Path | What it is | Status |
| --- | --- | --- |
| `packages/cycle_engine` | Python engine: range prediction, FIGO cycle norms, PBAC flow scoring, PMS/mood cyclicity (incl. cravings), period-pain guide, pain timing/duration/impact, treatment before-and-after, red-flag rules, doctor brief | Working; includes personal pain "function line", irregular-cycle mode, CSV export |
| `services/api` | FastAPI backend: WhatsApp Cloud API webhook, onboarding + consent, 5-language bot, rule-based log extraction, Sarvam speech-to-text for voice notes | Working with encrypted SQLite store (or in-memory for dev); PLAN, WRONG, EXPORT, DISCREET, PROMISE commands and a "did this help?" check-in |
| `services/mcp` | MCP server (Python SDK 2.x) exposing read-only tools: cycle status, trends, flags, doctor brief | Working on demo data, 2 tests |
| `apps/mobile` | Flutter Android app shell: today screen, quick log (flow, pain, mood, cravings), pain-relief screen, language switcher | Skeleton, checked in CI |
| `docs/` | Architecture, decisions, clinical rules, privacy data map | Living docs |

Product requirements and the marketing plan live as shared docs — links in [`docs/product/README.md`](docs/product/README.md).

## Direction: pain first

The first release owns one journey: **period pain and delayed recognition**. A woman describes her pain in her own language, we turn it into a structured history (timing, place, intensity, duration, nausea, what she missed, what helped), flag warning signs, and give her a report a gynaecologist can read in a minute. Mood, perimenopause and treatment follow-up build on the same record.

Deliberately out of v1: fertility and ovulation features (calendar day-counting can't establish ovulation or hormonal phase, so the engine only says "N days before your expected period"), doctor booking (referral to a partner first), and any diagnosis or dosing.

## Quick start

```bash
# Python 3.11+
python -m venv .venv && source .venv/bin/activate
pip install -e "packages/cycle_engine[dev]" -e "services/api[dev]" -e "services/mcp[dev]"
pytest packages/cycle_engine services/api services/mcp

# WhatsApp bot locally
cp .env.example .env   # fill in Meta + Sarvam keys
cd services/api && uvicorn app.main:app --reload --port 8000
# expose with a tunnel and set https://<tunnel>/webhooks/whatsapp as the callback URL in Meta's console

# MCP connector with demo data (stdio) — add to Claude Desktop:
#   {"mcpServers": {"cycle-companion": {"command": "companion-mcp"}}}
companion-mcp
```

Android app: see [`apps/mobile/README.md`](apps/mobile/README.md).

## Ground rules

- **Flag, don't diagnose.** Red flags come from fixed rules in `cycle_engine.red_flags`, signed off by a clinician — never from an LLM.
- **No doses, ever.** Pain guidance points to the pack label or a pharmacist.
- **Consent before storage**, data in India, delete on request. See [SECURITY.md](SECURITY.md).
- **Translations are drafts** until a native speaker and the clinical advisor approve them.

## License

Proprietary. All rights reserved.
