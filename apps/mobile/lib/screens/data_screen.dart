import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../engine/export.dart';
import '../l10n/strings.dart';
import 'log_sheet.dart';

/// Her data, as a table she can paste into Excel or Sheets. Free, always.
class DataScreen extends StatelessWidget {
  const DataScreen({super.key, required this.logs});

  final List<DailyLog> logs;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final csv = exportCsv(logs);
    return Scaffold(
      appBar: AppBar(title: Text(s.get('myData'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(s.get('export_head')),
          const SizedBox(height: 12),
          FilledButton.icon(
            icon: const Icon(Icons.copy),
            label: Text(s.get('copy')),
            onPressed: () async {
              await Clipboard.setData(ClipboardData(text: csv));
              if (!context.mounted) return;
              ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s.get('copied'))));
            },
          ),
          const SizedBox(height: 12),
          SelectableText(csv, style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
          const SizedBox(height: 24),
          Text(s.get('promiseApp'), style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}
