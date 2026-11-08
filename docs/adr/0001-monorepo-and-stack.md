# ADR 0001 — Monorepo and stack

**Status:** accepted (Nov 2026)

## Decision

- One repo: `packages/` (shared logic), `services/` (backend, MCP), `apps/` (mobile), `docs/`.
- **Backend:** Python + FastAPI. Founder's strongest language; fastest path for ML/NLP work.
- **Engine:** dependency-free Python package, fully unit-tested; portable to Dart later.
- **Mobile:** Flutter, Android first. One codebase gives iOS later; Material widgets render Indic scripts well; Health Connect has Flutter plugins.
- **Speech:** Sarvam AI speech-to-text (Kannada, Hindi, Telugu, Tamil, English, code-mixed).
- **MCP:** official Python SDK 2.x (`MCPServer`), stdio for dev, streamable HTTP + OAuth 2.1 for production.
- **CI:** GitHub Actions — pytest per Python package, `flutter analyze` + `flutter test` for the app.

## Alternatives considered

- Kotlin native Android: best platform access, but no iOS path and slower for a solo founder new to mobile.
- React Native: fine, but splits the team across TypeScript and Python with no gain over Flutter here.
