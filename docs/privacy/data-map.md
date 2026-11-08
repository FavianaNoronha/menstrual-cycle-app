# Data map (DPDP Act 2023 / DPDP Rules 2025)

Core consent, breach-reporting and children's-data duties apply from 14 May 2027. Build them in now.

| Data | Why we need it | Where it lives | Retention | Shared with |
| --- | --- | --- | --- | --- |
| WhatsApp number | Identify the user on WhatsApp | API DB (India), hashed index | Until deletion | Meta (as message transport only) |
| Language, consent timestamp | Onboarding, proof of consent | API DB | Until deletion + consent log per Rules | — |
| Period dates, flow, pain, symptoms, cravings | The product | API DB, field-level encrypted; app local DB | Until deletion | Nobody. MCP clients only with user-granted scopes |
| Voice notes | Transcription | Not stored; streamed to STT, discarded | 0 days | Sarvam AI (processor; contract must bar training use) |
| Age | Norms (FIGO regularity limits, perimenopause hints) | API DB | Until deletion | — |
| App analytics | Product health | Self-hosted, no health fields | 13 months | — |

Rules:
- Under-18 users need verifiable parental consent → v1 is 18+ only.
- No ad SDKs or marketing pixels in the app or on pages that carry health data.
- "DELETE" (WhatsApp) / "Delete my data" (app) erases the record; backups purge within the documented window.
- Breach: report to the Data Protection Board within 72 hours and inform affected users.


## Storage as built (pilot)

- `SqliteStore` encrypts each user's record with Fernet before writing. The phone number is not a column: rows are keyed by an HMAC of it and the number lives only inside the encrypted blob. De-duplication ids are stored hashed and purged after 7 days.
- `STORE_KEY` lives outside the repo and the database host. Losing it loses all data; the store refuses to start with a wrong key rather than silently resetting users.
- Sending DELETE removes the user's row. Backups must be encrypted with the same discipline and expire on a schedule so deletion is real.
- Before a public launch: Postgres in an India region, key rotation, audit logging, and a breach-notification runbook (DPDP: 72 hours).
