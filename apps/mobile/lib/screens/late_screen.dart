import 'package:flutter/material.dart';

import '../engine/cycle_engine.dart';
import '../l10n/strings.dart';

/// Calm, non-judgemental help when a period is late. No assumptions about why she is asking.
class LateScreen extends StatelessWidget {
  const LateScreen({super.key, required this.starts, required this.misses});

  final List<DateTime> starts;
  final int misses;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final pred = predictNextPeriod(starts, misses: misses);
    String fmtDate(DateTime d) => '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}';
    return Scaffold(
      appBar: AppBar(title: Text(s.get('periodLate'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(s.get('late')),
          const SizedBox(height: 16),
          if (pred != null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(s.fmt('status', {
                  'cycle_day': '${daysBetween(([...starts]..sort()).last, DateTime.now()) + 1}',
                  'likely': fmtDate(pred.likely),
                  'earliest': fmtDate(pred.earliest),
                  'latest': fmtDate(pred.latest),
                })),
              ),
            ),
        ],
      ),
    );
  }
}
