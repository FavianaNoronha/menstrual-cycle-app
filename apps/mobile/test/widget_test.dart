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

  test('unknown keys fall back to the key', () {
    expect(S(const Locale('ta')).get('nope'), 'nope');
  });
}
