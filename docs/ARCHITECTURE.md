# Architecture (v1)

```
 WhatsApp user ──► Meta Cloud API ──► services/api (FastAPI, India region)
   text / voice                         ├─ signature check, dedupe
                                        ├─ onboarding: language → consent (DPDP)
                                        ├─ voice note → Sarvam STT (code-mixed Indian languages)
                                        ├─ extraction: rule lexicon → (later) LLM with JSON schema → read-back
                                        ├─ cycle_engine: prediction, norms, PBAC, cyclicity, pain, red flags
                                        └─ store: Postgres, field-level encryption (dev: memory)

 Android app (Flutter) ──► encrypted on-device DB ──sync──► services/api
 Claude / ChatGPT ──► services/mcp (MCP, OAuth 2.1, read-only scopes) ──► same record
```

## Decisions and corrections

- **Where the record lives.** The earlier concept said "on her phone". WhatsApp messages and the MCP connector both terminate on our server, so v1 keeps an encrypted server-side record in an Indian region, with the app caching locally. A "phone-only" mode (no WhatsApp, no connector) can come later for users who want it.
- **One engine, two runtimes.** The engine is dependency-free Python so it can be ported to Dart for offline use; the server stays the source of truth.
- **WhatsApp policy.** Meta bars general-purpose AI assistants on the Business API (from 15 Jan 2026). The bot is scoped to cycle tracking and refuses off-topic chat.
- **WhatsApp costs.** From 1 Oct 2026, service replies are free up to 1,000 per number per month, then charged; utility templates are charged even inside the 24-hour window. Design nudges so the user messages first where possible, and budget per active user.
- **LLM use.** Only for extraction (to a fixed schema, read back for confirmation) and for phrasing answers from her record plus vetted guidance. Never for red flags. Inference must run in India; provider is an open decision.

See `docs/adr/` for decision records.
