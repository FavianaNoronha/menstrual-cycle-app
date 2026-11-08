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
