import 'package:flutter/material.dart';

import '../l10n/strings.dart';

/// "My cramps are bad": warning signs first, then self-care ordered by evidence.
/// Never shows medicine doses (see docs/clinical/pain-relief.md).
class PainReliefScreen extends StatelessWidget {
  const PainReliefScreen({super.key});

  static const List<(IconData, String)> _tips = [
    (Icons.local_fire_department_outlined, 'heatTip'),
    (Icons.medication_outlined, 'painkillerTip'),
    (Icons.directions_walk, 'movementTip'),
    (Icons.emoji_food_beverage_outlined, 'gingerTip'),
  ];

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text(s.get('painHelpTitle'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            color: scheme.errorContainer,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    s.get('warningTitle'),
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(color: scheme.onErrorContainer),
                  ),
                  const SizedBox(height: 8),
                  Text(s.get('warningList'), style: TextStyle(color: scheme.onErrorContainer)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          for (final (icon, key) in _tips)
            ListTile(leading: Icon(icon), title: Text(s.get(key))),
          const Divider(),
          Padding(
            padding: const EdgeInsets.all(8),
            child: Text(s.get('seeDoctor')),
          ),
        ],
      ),
    );
  }
}
