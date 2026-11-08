import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'l10n/strings.dart';
import 'screens/today_screen.dart';

void main() {
  runApp(const RituApp());
}

class RituApp extends StatefulWidget {
  const RituApp({super.key});

  @override
  State<RituApp> createState() => _RituAppState();
}

class _RituAppState extends State<RituApp> {
  Locale _locale = const Locale('en');

  void _setLocale(Locale locale) => setState(() => _locale = locale);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Ritu',
      debugShowCheckedModeBanner: false,
      locale: _locale,
      supportedLocales: S.supported,
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      // Deliberately not pink: research on period apps found users dislike stereotyped,
      // non-discreet designs; a calm palette also helps on shared phones.
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2E6B5E)),
        useMaterial3: true,
      ),
      home: TodayScreen(onLocaleChanged: _setLocale),
    );
  }
}
