import 'package:flutter/material.dart';

import '../l10n/strings.dart';

/// One day's quick log. Mirrors cycle_engine's FlowLog, PainLog, SleepLog and SymptomLog.
class DailyLog {
  DailyLog({
    required this.day,
    this.periodStarted = false,
    this.flow,
    this.pain = 0,
    this.moods = const {},
    this.cravings = const {},
    this.painDurationMinutes,
    this.nausea = false,
    this.impacts = const {},
    this.sleepHours,
  });

  final DateTime day;
  final bool periodStarted;
  final String? flow; // light / medium / heavy
  final int pain; // 0-10
  final Set<String> moods; // mood_low, irritability, anxiety, mood_swings, energy_low
  final Set<String> cravings; // sweet, salty, spicy, fried
  final int? painDurationMinutes; // only set when pain > 0
  final bool nausea; // nausea or vomiting with the pain
  final Set<String> impacts; // work, school, sleep: what the pain stopped
  final double? sleepHours;
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
  int? _durationMinutes;
  bool _nausea = false;
  final Set<String> _impacts = {};
  double? _sleepHours;

  // Chips instead of typing: label key -> value stored.
  static const Map<String, int> _durationChoices = {
    'durShort': 15, // under 30 minutes
    'durHours': 90, // 1-2 hours
    'durLong': 240, // 3 hours or more
    'durAllDay': 1440,
  };
  static const Map<String, double> _sleepChoices = {
    'sleepLow': 4, // under 5 hours
    'sleepMid': 5.5,
    'sleepGood': 7.5,
    'sleepHigh': 9,
  };
  static const List<String> _impactKeys = ['work', 'school', 'sleep'];

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
        painDurationMinutes: _pain > 0 ? _durationMinutes : null,
        nausea: _pain > 0 && _nausea,
        impacts: _pain > 0 ? Set.of(_impacts) : const {},
        sleepHours: _sleepHours,
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
              if (_pain > 0) ...[
                Text(s.get('painLasted'), style: textTheme.titleMedium),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: [
                    for (final entry in _durationChoices.entries)
                      ChoiceChip(
                        label: Text(s.get(entry.key)),
                        selected: _durationMinutes == entry.value,
                        onSelected: (selected) => setState(() => _durationMinutes = selected ? entry.value : null),
                      ),
                  ],
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: [
                    FilterChip(
                      label: Text(s.get('nausea')),
                      selected: _nausea,
                      onSelected: (selected) => setState(() => _nausea = selected),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(s.get('painStopped'), style: textTheme.titleMedium),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: [
                    for (final key in _impactKeys)
                      FilterChip(
                        label: Text(s.get('impact_$key')),
                        selected: _impacts.contains(key),
                        onSelected: (selected) => setState(() {
                          selected ? _impacts.add(key) : _impacts.remove(key);
                        }),
                      ),
                  ],
                ),
                const SizedBox(height: 16),
              ],
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
              const SizedBox(height: 16),
              Text(s.get('sleepLastNight'), style: textTheme.titleMedium),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 4,
                children: [
                  for (final entry in _sleepChoices.entries)
                    ChoiceChip(
                      label: Text(s.get(entry.key)),
                      selected: _sleepHours == entry.value,
                      onSelected: (selected) => setState(() => _sleepHours = selected ? entry.value : null),
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
