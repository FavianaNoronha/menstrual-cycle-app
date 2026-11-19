import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:companion_mobile/l10n/strings.dart';
import 'package:companion_mobile/main.dart';

void main() {
  testWidgets('home screen shows the log and pain buttons', (tester) async {
    await tester.pumpWidget(const CompanionApp());
    expect(find.text('Log how you feel'), findsOneWidget);
    expect(find.text('My cramps are bad'), findsOneWidget);
  });

  test('every string has all five languages', () {
    for (final locale in S.supported) {
      final s = S(locale);
      expect(s.get('appTitle'), isNotEmpty);
      expect(s.get('warningList'), isNot('warningList'));
    }
  });

  test('new pain-detail strings exist in all five languages', () {
    const keys = [
      'painLasted', 'durShort', 'durHours', 'durLong', 'durAllDay', 'nausea', 'painStopped',
      'impact_work', 'impact_school', 'impact_sleep', 'sleepLastNight', 'sleepLow', 'sleepMid', 'sleepGood', 'sleepHigh',
    ];
    for (final locale in S.supported) {
      for (final key in keys) {
        expect(S(locale).get(key), isNot(key), reason: '$key missing for ${locale.languageCode}');
      }
    }
  });

  test('plan, late, data and promise strings exist in all five languages', () {
    const keys = [
      'myPlan', 'periodLate', 'myData', 'predictionWrong', 'copy', 'copied', 'irregularNote', 'doctorNote', 'promiseApp',
      'plan_head', 'plan_steps', 'late', 'wrong_ack', 'status', 'export_head', 'line_basis_personal', 'line_basis_default',
    ];
    for (final locale in S.supported) {
      for (final key in keys) {
        expect(S(locale).get(key), isNot(key), reason: '$key missing for ${locale.languageCode}');
      }
    }
  });

  test('fmt fills placeholders', () {
    final out = S(const Locale('en')).fmt('plan_head', {'line': '6', 'basis': 'x'});
    expect(out, contains('6/10'));
    expect(out, isNot(contains('{')));
  });

  testWidgets('home screen has plan, late and data buttons', (tester) async {
    await tester.pumpWidget(const CompanionApp());
    await tester.scrollUntilVisible(find.text('My data (export)'), 200, scrollable: find.byType(Scrollable).first);
    expect(find.text('My pain plan'), findsOneWidget);
    expect(find.text('My period is late'), findsOneWidget);
  });

  test('unknown keys fall back to the key', () {
    expect(S(const Locale('ta')).get('nope'), 'nope');
  });
}
