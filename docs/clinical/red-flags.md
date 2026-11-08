# Red-flag rules (source of truth)

Implemented in `packages/cycle_engine/src/cycle_engine/red_flags.py` and `pain.py`.
**Status: DRAFT — every rule needs clinical advisor sign-off before launch.** Record the reviewer and date per rule.

| Code | Trigger | Severity | User sees | Reviewed by / date |
| --- | --- | --- | --- | --- |
| soaking_hourly | Soaking a pad within an hour for 2+ hours in a row | URGENT | Seek care today; 112 / 108 | |
| pain_with_fainting | Fainting or dizziness logged with pain or bleeding | URGENT | Seek care today | |
| one_sided_pain_pregnancy_possible | One-sided pain + positive test or pregnancy possible | URGENT | Seek care today (possible ectopic) | |
| bleeding_with_positive_test | Bleeding while pregnancy test positive | URGENT | Seek care today | |
| pain_with_fever_or_discharge | Fever or unusual discharge with pain (urgent if pain ≥ 8) | SOON / URGENT | See a doctor soon / today | |
| painkillers_not_helping | Painkiller didn't help in 3+ cycles | SOON | Book a visit; brief | |
| heavy_bleeding_pattern | PBAC > 100 (or cup > 80 mL) in 2 of last 3 periods | SOON | Book a visit; ask about Hb/iron | |
| bleeding_after_menopause | Bleeding after 12+ months without periods, age ≥ 40 | SOON | Book a visit promptly | |
| no_period_90_days | No period for 90+ days, not pregnant | SOON | Book a visit | |
| bleeding_prolonged | Bleeding > 8 days in 2+ periods | SOON | Book a visit | |
| cycles_irregular / frequent / infrequent | Outside FIGO limits (24–38 days; variation ≤ 7–9 days by age) | DISCUSS | In doctor brief | |
| pain_pattern_bowel_bladder_sex | Pain with bowel, bladder or sex in 2+ cycles | DISCUSS | In doctor brief | |
| pain_outside_periods | Pain ≥ 4/10 outside periods on 3+ days in 60 days | DISCUSS | In doctor brief | |
| pain_worsening / pain_severe_recurrent | Peak pain rising 2+ points over 3 cycles / ≥ 8 in 2+ cycles | DISCUSS | In doctor brief | |
| transition_early_signs / late_signs | Age ≥ 35: ≥ 7-day swings in consecutive cycles twice / gap ≥ 60 days (STRAW+10) | DISCUSS | In doctor brief | |

Sources: FIGO AUB System 1 (2018); STRAW+10 (Harlow et al. 2012); NICE CKS dysmenorrhoea; PBAC (Higham 1990).
