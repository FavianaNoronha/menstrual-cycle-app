# Going live on WhatsApp (and the app)

## What only you can do (Meta and legal; I can't do these for you)
1. **Meta Business account** at business.facebook.com, then verify the business (needs business documents; can take days). Until verified you can still test with up to 5 recipient numbers.
2. **A phone number for the bot** that is NOT already registered on WhatsApp. Use a new SIM or a number you will dedicate to this.
3. **WhatsApp Cloud API app** at developers.facebook.com: create an app, add the WhatsApp product, note the *phone number ID*, make a *permanent access token* (system user), and note the *app secret*.
4. **Display name and a message template** for proactive messages (the heads-up). Replies inside 24 hours of her last message need no template; anything we start does. Submit the template text from `nudge_discreet` first since it names nothing.
5. **Sarvam API key** (voice notes) from sarvam.ai.
6. **A privacy policy page** (Meta requires a URL) and a DPDP-compliant consent notice. Have a lawyer review it. 18+ only for now.

## What goes on a server (I wrote the Dockerfile)
```
docker build -t cycle-companion .
docker run -d -p 8000:8000 -v cc-data:/data --env-file .env cycle-companion
```
Host it in an India region (AWS Mumbai/Hyderabad, or similar) behind HTTPS. Meta needs a public HTTPS URL.

`.env` (see `.env.example`): `WHATSAPP_VERIFY_TOKEN` (any long random string you choose), `WHATSAPP_APP_SECRET`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `SARVAM_API_KEY`, `STORE_KEY` (generate: `python -m app.store.sqlite genkey`; **back it up; lose it and all data is unreadable**).

## Connect
In the Meta app, WhatsApp > Configuration: callback URL `https://YOUR-DOMAIN/webhooks/whatsapp`, verify token = yours, subscribe to `messages`. Send "hi" from a test number.

## Before real users (checklist)
- [ ] Native-speaker + clinician review of all 4 Indian-language drafts (esp. urgent and doctor lines)
- [ ] 25 test users through `docs/research/interview-script.md` first
- [ ] Privacy policy live; consent text matches `docs/privacy/data-map.md`
- [ ] Backups of the database volume and STORE_KEY
- [ ] Scheduler for proactive nudges + approved template (not built yet; nudges currently go out only alongside a reply)
- [ ] Meta's WhatsApp Business AI policy re-read: our bot is scoped to cycle health and refuses off-topic chat

## The Android app
The Flutter app in `apps/mobile` has never been compiled. Next steps: build it in CI (`.github/workflows/android-apk.yml` exists; needs the repo on GitHub), add screens for the pain line, PLAN, EXPORT and WRONG, and sync with the same engine via the API. The WhatsApp bot and the app should share one account per phone number so a user can switch freely.
