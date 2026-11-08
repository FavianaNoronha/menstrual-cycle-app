# Ritu

**Cycle health in your language.** An Android app and WhatsApp bot that turn period, flow, pain and mood logs into clinically useful insight — in English, Hindi, Kannada, Telugu and Tamil — plus an MCP connector so Claude, ChatGPT and other assistants can read a woman's cycle summary with her consent.

> Working name. "RITU" is already used by a PCOS tracker on Google Play — see the marketing plan before investing in the brand.

## What's in this repo

| Path | What it is | Status |
| --- | --- | --- |
| `packages/cycle_engine` | Python engine: range prediction, FIGO cycle norms, PBAC flow scoring, PMS/mood cyclicity (incl. cravings), period-pain guide, red-flag rules, doctor brief | Working, 28 tests |
| `services/api` | FastAPI backend: WhatsApp Cloud API webhook, onboarding + consent, 5-language bot, rule-based log extraction, Sarvam speech-to-text for voice notes | Working with in-memory store, 26 tests |
| `services/mcp` | MCP server (Python SDK 2.x) exposing read-only tools: cycle status, trends, flags, doctor brief | Working on demo data, 2 tests |
| `apps/mobile` | Flutter Android app shell: today screen, quick log (flow, pain, mood, cravings), pain-relief screen, language switcher | Skeleton, checked in CI |
| `docs/` | Architecture, decisions, clinical rules, privacy data map | Living docs |

Product requirements and the marketing plan live as shared docs — links in [`docs/product/README.md`](docs/product/README.md).

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
#   {"mcpServers": {"ritu": {"command": "ritu-mcp"}}}
ritu-mcp
```

Android app: see [`apps/mobile/README.md`](apps/mobile/README.md).

## Ground rules

- **Flag, don't diagnose.** Red flags come from fixed rules in `ritu_engine.red_flags`, signed off by a clinician — never from an LLM.
- **No doses, ever.** Pain guidance points to the pack label or a pharmacist.
- **Consent before storage**, data in India, delete on request. See [SECURITY.md](SECURITY.md).
- **Translations are drafts** until a native speaker and the clinical advisor approve them.

## License

Proprietary. All rights reserved.
