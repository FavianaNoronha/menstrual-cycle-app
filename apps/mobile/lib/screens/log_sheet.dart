import 'package:flutter/material.dart';

import '../l10n/strings.dart';

/// One day's quick log. Mirrors ritu_engine's FlowLog, PainLog and SymptomLog.
class DailyLog {
  DailyLog({
    required this.day,
    this.periodStarted = false,
    this.flow,
    this.pain = 0,
    this.moods = const {},
    this.cravings = const {},
  });

  final DateTime day;
  final bool periodStarted;
  final String? flow; // light / medium / heavy
  final int pain; // 0-10
  final Set<String> moods; // mood_low, irritability, anxiety, mood_swings, energy_low
  final Set<String> cravings; // sweet, salty, spicy, fried
}

class LogSheet extends StatefulWidget {
  const LogSheet({super.key});

  @override
  State<LogSheet> createState() => _LogSheetState();
}

class _LogSheetState extends State<LogSheet> {
  bool _periodStarted = false;
  String? _flow;
  double _pain = 0;
  final Set<String> _moods = {};
  final Set<String> _cravings = {};

  static const Map<String, String> _moodKeys = {
    'mood_low': 'moodLow',
    'irritability': 'irritable',
    'anxiety': 'anxious',
    'mood_swings': 'moodSwings',
    'energy_low': 'tired',
  };

  static const List<String> _cravingKeys = ['sweet', 'salty', 'spicy', 'fried'];

  void _save() {
    Navigator.of(context).pop(
      DailyLog(
        day: DateTime.now(),
        periodStarted: _periodStarted,
        flow: _flow,
        pain: _pain.round(),
        moods: Set.of(_moods),
        cravings: Set.of(_cravings),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final textTheme = Theme.of(context).textTheme;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          left: 16,
          right: 16,
          top: 16,
          bottom: MediaQuery.of(context).viewInsets.bottom + 16,
        ),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(s.get('periodStarted')),
                value: _periodStarted,
                onChanged: (v) => setState(() => _periodStarted = v),
              ),
              Text(s.get('flow'), style: textTheme.titleMedium),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  for (final level in const ['light', 'medium', 'heavy'])
                    ChoiceChip(
                      label: Text(s.get(level)),
                      selected: _flow == level,
                      onSelected: (selected) => setState(() => _flow = selected ? level : null),
                    ),
                ],
              ),
              const SizedBox(height: 16),
              Text('${s.get('pain')}: ${_pain.round()}/10', style: textTheme.titleMedium),
              Slider(
                value: _pain,
                min: 0,
                max: 10,
                divisions: 10,
                label: _pain.round().toString(),
                onChanged: (v) => setState(() => _pain = v),
              ),
              Text(s.get('mood'), style: textTheme.titleMedium),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 4,
                children: [
                  for (final entry in _moodKeys.entries)
                    FilterChip(
                      label: Text(s.get(entry.value)),
                      selected: _moods.contains(entry.key),
                      onSelected: (selected) => setState(() {
                        selected ? _moods.add(entry.key) : _moods.remove(entry.key);
                      }),
                    ),
                ],
              ),
              const SizedBox(height: 16),
              Text(s.get('cravings'), style: textTheme.titleMedium),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  for (final key in _cravingKeys)
                    FilterChip(
                      label: Text(s.get(key)),
                      selected: _cravings.contains(key),
                      onSelected: (selected) => setState(() {
                        selected ? _cravings.add(key) : _cravings.remove(key);
                      }),
                    ),
                ],
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: FilledButton(onPressed: _save, child: Text(s.get('save'))),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
