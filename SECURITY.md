# Security and privacy

Ritu handles menstrual and health data — among the most sensitive data a person has.

## Rules for everyone working on this repo

1. **No real user data outside production.** Not in issues, tests, logs, screenshots or Slack. Use made-up records.
2. **No health data in third-party tools.** Analytics, crash reporting and ad SDKs never receive health fields, and the app ships with no ad or marketing pixels (Meta treats health apps as a restricted category anyway).
3. **Secrets live in a secrets manager**, never in code or `.env` files committed to git.
4. **Data stays in India.** Production databases, backups and AI inference run in Indian regions.
5. **Consent before storage.** Nothing health-related is saved before the user agrees (DPDP Act 2023 / DPDP Rules 2025).
6. **Delete means delete.** "DELETE" on WhatsApp or "Delete my data" in the app removes the record and backups within the documented window.

## Reporting a vulnerability

Email the founder directly (do not open a public issue). We aim to acknowledge within 48 hours.
Personal-data breaches must be reported to the Data Protection Board and affected users as required by the DPDP Rules (72-hour reporting to the Board).
