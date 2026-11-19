import '../screens/log_sheet.dart';

String _cell(Object? v) {
  final s = '${v ?? ''}';
  return s.contains(',') || s.contains('"') || s.contains('\n') ? '"${s.replaceAll('"', '""')}"' : s;
}

String _iso(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

/// Everything she logged as CSV (type,date,value,notes), same shape as the bot's EXPORT.
String exportCsv(List<DailyLog> logs) {
  final sorted = [...logs]..sort((a, b) => a.day.compareTo(b.day));
  final rows = <List<Object?>>[
    ['type', 'date', 'value', 'notes'],
  ];
  for (final l in sorted) {
    final d = _iso(l.day);
    if (l.periodStarted) rows.add(['period_start', d, '', '']);
    if (l.flow != null) rows.add(['flow', d, l.flow, '']);
    if (l.pain > 0 || l.impacts.isNotEmpty) rows.add(['pain', d, l.pain, (l.impacts.toList()..sort()).join(';')]);
    for (final m in (l.moods.toList()..sort())) {
      rows.add(['symptom', d, '', m]);
    }
    for (final c in (l.cravings.toList()..sort())) {
      rows.add(['craving', d, '', c]);
    }
    if (l.sleepHours != null) rows.add(['sleep_hours', d, l.sleepHours, '']);
  }
  return rows.map((r) => r.map(_cell).join(',')).join('\n');
}
