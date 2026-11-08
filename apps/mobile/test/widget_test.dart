import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ritu_mobile/l10n/strings.dart';
import 'package:ritu_mobile/main.dart';

void main() {
  testWidgets('home screen shows the log and pain buttons', (tester) async {
    await tester.pumpWidget(const RituApp());
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

  test('unknown keys fall back to the key', () {
    expect(S(const Locale('ta')).get('nope'), 'nope');
  });
}
