# Ritu Android app (Flutter)

Skeleton: today screen, quick log (period started, flow, pain 0–10, mood, cravings), "My cramps are bad" relief screen, and a language switcher for English, Hindi, Kannada, Telugu and Tamil.

## First-time setup

```bash
# Install Flutter (stable): https://docs.flutter.dev/get-started/install
cd apps/mobile
flutter create . --org in.ritu --platforms android   # generates android/ without touching lib/
flutter pub get
flutter run                                          # with an Android device or emulator connected
```

## Next steps

1. Encrypted local storage (e.g. drift + SQLCipher) and an app lock (PIN/biometric) — many Indian women use shared phones.
2. Discreet mode: neutral app name/icon option and notifications that never say "period".
3. Sync with `services/api`, and port the engine's prediction + red flags to Dart for offline use.
4. Voice logging button (record → API → read-back).
5. PBAC pictogram logging with Indian products (pads, cloth, cups) and coin-size clot references.

Translations in `lib/l10n/strings.dart` are DRAFTS — native-speaker and clinical review required.
