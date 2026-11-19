# Claims we can and can't make

CDSCO's Medical Device Software guidance (21 July 2026) leaves general wellness apps out of scope, but software with a medical purpose is regulated (classes A–D). Google Play also requires the Health apps declaration and disclaimers for health claims. Keep v1 a wellness and record-keeping product.

| OK (wellness, records) | Not OK in v1 (device territory) |
| --- | --- |
| Track and summarise your cycle, flow, pain and mood | "Detects / screens for PCOS, PMDD, endometriosis, anaemia" |
| "Your cycles are outside the typical range — consider a doctor visit" | "You have heavy menstrual bleeding" |
| "Share this summary with your doctor" | Contraception, "safe days", fertility window as birth control |
| "Symptoms that rise before your period" | "You have PMDD" |

Marketing and influencer content follows the same table. Influencers giving technical health advice must hold relevant qualifications and disclose them (ASCI guidelines, updated April 2025).


## Cycle windows, not hormonal phases

The engine reports `bleeding`, `before_period`, `between` and `overdue`, plus days to the expected period. It never labels a day follicular, ovulatory or luteal: counting days from the last period cannot confirm phase or ovulation (BMJ analysis, Sept 2026). Do not add phase-based exercise or diet advice.

## Treatment follow-up

Before-and-after pain comparison is shown as an observed change in her own logs, only after 2+ cycles on each side, and always with "does not show the treatment caused it". The app never suggests a treatment.

## Personal function line and pre-period heads-up

- The "function line" is the median, across her cycles, of the lowest pain score on a day pain stopped something she does (work, school, sleep, exercise, housework). Until two cycles with such logs exist it shows 6/10 labelled as a typical starting value, not hers. Published interference cut-offs (moderate about 5-6, severe 7+) vary between people, so we never present 6 as a norm.
- Wording rule: the goal is to stay below her line, never to "tolerate more". Women with period pain can have heightened pain sensitivity, so no message coaches endurance.
- The pre-period heads-up fires only when pain reached her line in 2 of her last 3 cycles with pain logs, and only 0-2 days before the predicted period, once per predicted date. It says to have ready what she already uses and to follow the pack or ask a pharmacist. It never names a drug or dose.
- Starting a pain medicine early is mainstream guidance, but evidence for specific timing is modest; the message is a prompt, not an instruction.
- If pain reaches her line in 2+ recent cycles, the plan suggests a doctor and offers BRIEF.
- DISCREET mode swaps unprompted messages for a neutral reminder ("a note is waiting"). It never changes safety or red-flag messages, or read-backs she asked for.

## Irregular cycles and prediction feedback

- A cycle history is flagged irregular only with 3+ cycle lengths, and only if the longest and shortest differ by 9+ days or any is outside 21-38 days (FIGO normal interval). Two cycles are never called irregular.
- For irregular histories the range is the full span she has actually had, not a percentile, and confidence is always LOW. We say so and suggest a doctor "can check for common causes like PCOS or thyroid". We never say she has either.
- WRONG widens the range by 2 days per side per press, at most 3 presses, so a few taps cannot make the range meaningless. It is her feedback on the range, not a medical signal.
- The note about a doctor is a prompt, not a diagnosis. Wording must be reviewed by the clinical advisor.

## Data export and "did this help?"

- EXPORT returns exactly what she logged, as CSV text. It adds no interpretation.
- After PLAN and BRIEF we ask one question (1 yes / 2 a bit / 3 no). A "no" asks for a reason in her words (200 characters kept). Answers are stored with her record, deleted by DELETE, and only counts are ever reported (`python -m app.store.sqlite feedback`). This is product feedback, never a health signal.
