import 'package:flutter_test/flutter_test.dart';
import 'package:companion_mobile/engine/cycle_engine.dart';

List<DateTime> startsFor(List<int> lengths) {
  var d = DateTime(2026, 1, 1);
  final out = [d];
  for (final n in lengths) {
    d = addDays(d, n);
    out.add(d);
  }
  return out;
}

int width(Prediction p) => daysBetween(p.earliest, p.latest);

void main() {
  test('regular cycles are not irregular and the range is narrow', () {
    final p = predictNextPeriod(startsFor([28, 29, 28, 27, 28, 28]))!;
    expect(p.irregular, isFalse);
    expect(width(p), lessThanOrEqualTo(6));
  });

  test('wide spread is irregular and the range covers every observed length', () {
    final starts = startsFor([24, 45, 31, 52]);
    expect(isIrregular([24, 45, 31, 52]), isTrue);
    final p = predictNextPeriod(starts)!;
    final last = starts.last;
    expect(p.irregular, isTrue);
    expect(p.lowConfidence, isTrue);
    expect(!p.earliest.isAfter(addDays(last, 24)), isTrue);
    expect(!p.latest.isBefore(addDays(last, 52)), isTrue);
  });

  test('two cycles are never called irregular', () {
    expect(isIrregular([20, 60]), isFalse);
  });

  test('"this date is wrong" widens by 2 days a side, at most 3 presses', () {
    final starts = startsFor([28, 28, 29, 28, 28]);
    final base = width(predictNextPeriod(starts)!);
    expect(width(predictNextPeriod(starts, misses: 1)!), base + 4);
    expect(width(predictNextPeriod(starts, misses: 50)!), base + 12);
  });

  test('no periods logged gives no prediction; one gives a wide default range', () {
    expect(predictNextPeriod([]), isNull);
    final p = predictNextPeriod([DateTime(2026, 1, 1)])!;
    expect(width(p), 14);
  });

  test('function line starts at 6 and becomes personal after 2 cycles with logs', () {
    final starts = startsFor([28, 28, 28]);
    expect(functionLine(starts, const []).score, defaultLine);
    final pain = [
      PainEntry(day: starts[0], score: 5, stoppedSomething: true),
      PainEntry(day: starts[1], score: 7, stoppedSomething: true),
      PainEntry(day: starts[2], score: 4, stoppedSomething: true),
    ];
    final line = functionLine(starts, pain);
    expect(line.personal, isTrue);
    expect(line.score, 5); // median of 5, 7, 4
    expect(painPlan(starts, pain).repeats, isTrue); // peaks 5, 7, 4 vs line 5: two cycles at or above
  });

  test('function line is clamped to 3-9', () {
    final starts = startsFor([28, 28]);
    final pain = [
      PainEntry(day: starts[0], score: 1, stoppedSomething: true),
      PainEntry(day: starts[1], score: 1, stoppedSomething: true),
    ];
    expect(functionLine(starts, pain).score, lineFloor);
  });
}
