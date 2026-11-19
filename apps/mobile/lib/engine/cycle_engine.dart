/// Dart port of the parts of packages/cycle_engine the app needs offline:
/// range prediction (with irregular mode and "this date is wrong" feedback) and the
/// personal pain "function line". Keep in step with the Python engine and its tests.
library;

import 'dart:math';

const int defaultCycleDays = 28;
const int maxHistory = 12;
const int outlierDays = 90;
const int irregularSpreadDays = 9;
const int normalCycleMin = 21;
const int normalCycleMax = 38;
const int missWidenDays = 2;
const int maxMissWidenPresses = 3;

const int defaultLine = 6;
const int minCyclesForPersonalLine = 2;
const int lineFloor = 3;
const int lineCeiling = 9;

DateTime dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);
DateTime addDays(DateTime d, int n) => DateTime(d.year, d.month, d.day + n);
int daysBetween(DateTime a, DateTime b) => dateOnly(b).difference(dateOnly(a)).inDays;

class Prediction {
  const Prediction({
    required this.earliest,
    required this.likely,
    required this.latest,
    required this.irregular,
    required this.lowConfidence,
  });

  final DateTime earliest;
  final DateTime likely;
  final DateTime latest;
  final bool irregular;
  final bool lowConfidence;
}

/// Days between consecutive period starts, oldest first.
List<int> cycleLengths(List<DateTime> starts) {
  final sorted = [...starts.map(dateOnly)]..sort();
  return [for (var i = 1; i < sorted.length; i++) daysBetween(sorted[i - 1], sorted[i])];
}

/// 3+ cycles that vary a lot or sit outside the normal 21-38 day interval.
bool isIrregular(List<int> lengths) {
  if (lengths.length < 3) return false;
  final spread = lengths.reduce(max) - lengths.reduce(min);
  return spread >= irregularSpreadDays || lengths.any((n) => n < normalCycleMin || n > normalCycleMax);
}

double _percentile(List<double> sorted, double q) {
  if (sorted.length == 1) return sorted.first;
  final pos = q * (sorted.length - 1);
  final lo = pos.floor();
  final hi = min(lo + 1, sorted.length - 1);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

double _median(List<double> sorted) {
  final n = sorted.length;
  return n.isOdd ? sorted[n ~/ 2] : (sorted[n ~/ 2 - 1] + sorted[n ~/ 2]) / 2;
}

/// Next period as an honest range. Returns null until one period is logged.
Prediction? predictNextPeriod(List<DateTime> periodStarts, {int misses = 0}) {
  if (periodStarts.isEmpty) return null;
  final sortedStarts = [...periodStarts.map(dateOnly)]..sort();
  final last = sortedStarts.last;
  var lengths = cycleLengths(sortedStarts).where((n) => n < outlierDays).toList();
  if (lengths.length > maxHistory) lengths = lengths.sublist(lengths.length - maxHistory);

  if (lengths.isEmpty) {
    return Prediction(
      earliest: addDays(last, defaultCycleDays - 7),
      likely: addDays(last, defaultCycleDays),
      latest: addDays(last, defaultCycleDays + 7),
      irregular: false,
      lowConfidence: true,
    );
  }

  final values = lengths.map((n) => n.toDouble()).toList()..sort();
  final mid = _median(values);
  final irregular = isIrregular(lengths);
  double lo;
  double hi;
  if (irregular) {
    lo = values.first;
    hi = values.last;
  } else if (values.length >= 4) {
    lo = _percentile(values, 0.10);
    hi = _percentile(values, 0.90);
  } else {
    lo = values.first - 2;
    hi = values.last + 2;
  }
  final widen = missWidenDays * min(misses, maxMissWidenPresses);
  lo -= widen;
  hi += widen;
  final spread = hi - lo;
  final low = irregular || misses > 0 || !(values.length >= 3 && spread <= 8);
  return Prediction(
    earliest: addDays(last, lo.round()),
    likely: addDays(last, mid.round()),
    latest: addDays(last, hi.round()),
    irregular: irregular,
    lowConfidence: low,
  );
}

class PainEntry {
  const PainEntry({required this.day, required this.score, required this.stoppedSomething});
  final DateTime day;
  final int score;
  final bool stoppedSomething;
}

class FunctionLine {
  const FunctionLine(this.score, {required this.personal, required this.cyclesUsed});
  final int score;
  final bool personal; // false = typical starting value
  final int cyclesUsed;
}

class PainPlan {
  const PainPlan({required this.line, required this.cyclesOverLine, required this.repeats});
  final FunctionLine line;
  final int cyclesOverLine; // of the last 3 cycles with pain logs
  final bool repeats; // at or above the line in 2+ recent cycles: suggest a doctor
}

List<List<PainEntry>> _painByPeriod(List<DateTime> starts, List<PainEntry> pain) {
  final sorted = [...starts.map(dateOnly)]..sort();
  return [
    for (final s in sorted)
      pain.where((p) {
        final d = dateOnly(p.day);
        return !d.isBefore(addDays(s, -2)) && !d.isAfter(addDays(s, 6));
      }).toList(),
  ];
}

/// Median, across cycles, of the lowest pain score on a day pain stopped something she does.
FunctionLine functionLine(List<DateTime> starts, List<PainEntry> pain) {
  final groups = _painByPeriod(starts, pain).where((g) => g.isNotEmpty);
  final lowest = <double>[
    for (final g in groups)
      if (g.any((p) => p.stoppedSomething)) g.where((p) => p.stoppedSomething).map((p) => p.score).reduce(min).toDouble(),
  ];
  if (lowest.length < minCyclesForPersonalLine) {
    return FunctionLine(defaultLine, personal: false, cyclesUsed: lowest.length);
  }
  lowest.sort();
  final score = max(lineFloor, min(lineCeiling, _median(lowest).round()));
  return FunctionLine(score, personal: true, cyclesUsed: lowest.length);
}

PainPlan painPlan(List<DateTime> starts, List<PainEntry> pain) {
  final line = functionLine(starts, pain);
  var groups = _painByPeriod(starts, pain).where((g) => g.isNotEmpty).toList();
  if (groups.length > 3) groups = groups.sublist(groups.length - 3);
  final over = groups.where((g) => g.map((p) => p.score).reduce(max) >= line.score).length;
  return PainPlan(line: line, cyclesOverLine: over, repeats: over >= 2);
}
