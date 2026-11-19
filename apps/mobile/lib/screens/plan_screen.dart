import 'package:flutter/material.dart';

import '../engine/cycle_engine.dart';
import '../l10n/strings.dart';

/// Her personal pain line and a plan. Never names a medicine or a dose.
class PlanScreen extends StatelessWidget {
  const PlanScreen({super.key, required this.starts, required this.pain});

  final List<DateTime> starts;
  final List<PainEntry> pain;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final plan = painPlan(starts, pain);
    final basis = s.get(plan.line.personal ? 'line_basis_personal' : 'line_basis_default');
    return Scaffold(
      appBar: AppBar(title: Text(s.get('myPlan'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(s.fmt('plan_head', {'line': '${plan.line.score}', 'basis': basis}),
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          Text(s.get('plan_steps')),
          if (plan.repeats) ...[
            const SizedBox(height: 12),
            Card(
              child: Padding(padding: const EdgeInsets.all(16), child: Text(s.get('doctorNote'))),
            ),
          ],
          const SizedBox(height: 24),
          Text(s.get('notDiagnosis'), style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}
