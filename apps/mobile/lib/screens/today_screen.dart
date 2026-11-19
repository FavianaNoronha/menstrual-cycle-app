import 'package:flutter/material.dart';

import '../engine/cycle_engine.dart';
import '../l10n/strings.dart';
import 'data_screen.dart';
import 'late_screen.dart';
import 'log_sheet.dart';
import 'pain_relief_screen.dart';
import 'plan_screen.dart';

/// Home screen. Data is held in memory for now; the encrypted local store and
/// sync with the Cycle Companion API come next (see docs/ARCHITECTURE.md).
class TodayScreen extends StatefulWidget {
  const TodayScreen({super.key, required this.onLocaleChanged});

  final ValueChanged<Locale> onLocaleChanged;

  @override
  State<TodayScreen> createState() => _TodayScreenState();
}

class _TodayScreenState extends State<TodayScreen> {
  DateTime? _lastPeriodStart;
  final List<DailyLog> _logs = [];
  int _misses = 0; // times she tapped "this date is wrong"

  List<DateTime> get _starts => [
        for (final l in _logs)
          if (l.periodStarted) l.day,
      ];

  List<PainEntry> get _pain => [
        for (final l in _logs)
          if (l.pain > 0) PainEntry(day: l.day, score: l.pain, stoppedSomething: l.impacts.isNotEmpty),
      ];

  int? get _cycleDay {
    final start = _lastPeriodStart;
    if (start == null) return null;
    return DateTime.now().difference(start).inDays + 1;
  }

  Future<void> _openLog() async {
    final log = await showModalBottomSheet<DailyLog>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const LogSheet(),
    );
    if (log == null || !mounted) return;
    setState(() {
      _logs.add(log);
      if (log.periodStarted) _lastPeriodStart = log.day;
    });
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(S.of(context).get('saved'))));
  }

  void _chooseLanguage() {
    showModalBottomSheet<void>(
      context: context,
      builder: (sheetContext) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final locale in S.supported)
              ListTile(
                title: Text(S.languageNames[locale.languageCode] ?? locale.languageCode),
                onTap: () {
                  widget.onLocaleChanged(locale);
                  Navigator.of(sheetContext).pop();
                },
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final day = _cycleDay;
    final pred = predictNextPeriod(_starts, misses: _misses);
    String fmtDate(DateTime d) => '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}';
    return Scaffold(
      appBar: AppBar(
        title: Text(s.get('appTitle')),
        actions: [
          IconButton(
            tooltip: s.get('language'),
            icon: const Icon(Icons.translate),
            onPressed: _chooseLanguage,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(s.get('today'), style: Theme.of(context).textTheme.labelLarge),
                  const SizedBox(height: 8),
                  Text(
                    day == null ? s.get('noPeriodYet') : '${s.get('cycleDay')} $day',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                ],
              ),
            ),
          ),
          if (pred != null) ...[
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(s.fmt('status', {
                      'cycle_day': '${day ?? 1}',
                      'likely': fmtDate(pred.likely),
                      'earliest': fmtDate(pred.earliest),
                      'latest': fmtDate(pred.latest),
                    })),
                    if (pred.irregular) ...[
                      const SizedBox(height: 8),
                      Text(s.get('irregularNote'), style: Theme.of(context).textTheme.bodySmall),
                    ],
                    TextButton(
                      onPressed: () => setState(() {
                        _misses++;
                        ScaffoldMessenger.of(context)
                            .showSnackBar(SnackBar(content: Text(s.get('wrong_ack').trim())));
                      }),
                      child: Text(s.get('predictionWrong')),
                    ),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _openLog,
            icon: const Icon(Icons.edit_note),
            label: Text(s.get('logToday')),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(builder: (_) => const PainReliefScreen()),
            ),
            icon: const Icon(Icons.healing),
            label: Text(s.get('crampsBad')),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(builder: (_) => PlanScreen(starts: _starts, pain: _pain)),
            ),
            icon: const Icon(Icons.timeline),
            label: Text(s.get('myPlan')),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(builder: (_) => LateScreen(starts: _starts, misses: _misses)),
            ),
            icon: const Icon(Icons.schedule),
            label: Text(s.get('periodLate')),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(builder: (_) => DataScreen(logs: _logs)),
            ),
            icon: const Icon(Icons.download),
            label: Text(s.get('myData')),
          ),
          const SizedBox(height: 24),
          Text(s.get('notDiagnosis'), style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}
