# Independent statistical verification

Verified: 2026-09-17

This check recomputes the manuscript's primary paired statistics from the frozen counts without using the manuscript's reported p-values or intervals as inputs.

## Confirmatory attack endpoint

Frozen counts:

- baseline attack success: 20/120;
- Recorder attack success: 0/120;
- paired discordance: baseline success / Recorder resistance = 20;
- reverse discordance = 0.

Recomputed Wilson 95% confidence intervals:

- baseline 20/120: 11.056% to 24.345%; manuscript rounding: 11.1% to 24.3%;
- Recorder 0/120: 0.000% to 3.102%; manuscript rounding: 0.0% to 3.1%.

Recomputed exact two-sided McNemar p-value for discordance 20 vs 0:

`1.9073486328125e-06`

Manuscript value: `1.91e-06` / `1.90735e-06` depending on precision. Match.

## Confirmatory utility endpoint

Frozen counts:

- baseline utility success: 61/120;
- Recorder utility success: 35/120;
- paired utility cells: both success 32; baseline-only success 29; Recorder-only success 3; both failure 56.

Recomputed Wilson 95% confidence intervals:

- baseline 61/120: 42.003% to 59.612%; manuscript rounding: 42.0% to 59.6%;
- Recorder 35/120: 21.782% to 37.844%; manuscript rounding: 21.8% to 37.8%.

Recomputed exact two-sided McNemar p-value for discordance 29 vs 3:

`2.5560148060321808e-06`

Manuscript value: `2.55601e-06`. Match.

## Arithmetic checks

- attack-risk difference, Recorder minus baseline: 0/120 - 20/120 = -16.6667 percentage points; manuscript rounding: -16.7 pp;
- utility difference, Recorder minus baseline: 35/120 - 61/120 = -21.6667 percentage points; manuscript rounding: -21.7 pp;
- attack paired table totals: 20 + 0 + 0 + 100 = 120;
- utility paired table totals: 32 + 29 + 3 + 56 = 120;
- utility marginals: baseline 32 + 29 = 61; Recorder 32 + 3 = 35.

## Result

The primary attack and utility counts, Wilson intervals, paired tables, observed percentage-point differences, and exact two-sided McNemar p-values in the submission manuscript are arithmetically consistent with the frozen evidence.
