# AgentDojo v2 paired utility analysis

**Date:** 2026-09-17  
**Status:** prespecified secondary analysis derived after primary-result freeze from the successful v2 artifact. No model calls, case selection, or policy changes were performed.

## Source

- GitHub Actions run: `35180860582`
- Artifact: `agentdojo-v2-35180860582`
- Artifact SHA-256: `3a4e8c97a8237b8f2fa5eae08f9fc2e4188c72173ff594a58680b7b907faac81`
- Frozen pair summary: `results/agentdojo/v2/summary.csv`
- Summary SHA-256: `a080ec60debde9746fd6e4d2b55ac38bf1900050f48bc609d5ec5b04a860041d`
- Primary frozen evidence: `docs/evidence/agentdojo-independent-v2-2026-09-17.md`

Protocol v2 prespecified that legitimate-task utility would be reported with paired discordant counts and exact McNemar testing. The original automated analysis recorded aggregate utility counts but did not emit the paired utility table. This document computes that declared secondary analysis directly from the frozen 120-pair summary.

## Paired utility outcomes

| Baseline utility | Flight Recorder utility | Pairs |
| --- | --- | ---: |
| success | success | 32 |
| success | failure | 29 |
| failure | success | 3 |
| failure | failure | 56 |

Aggregate utility therefore remains:

- Baseline: **61/120 (50.8%)**
- Agent Flight Recorder, `Review=deny`: **35/120 (29.2%)**
- Observed absolute difference: **-21.7 percentage points**

Wilson 95% confidence intervals for the condition proportions are:

- Baseline utility: **42.0% to 59.6%**
- Flight Recorder utility: **21.8% to 37.8%**

The discordant paired counts are 29 baseline-success/Recorder-failure pairs versus 3 baseline-failure/Recorder-success pairs. The exact two-sided McNemar p-value is **2.55601e-06**.

## Interpretation

The utility loss under the frozen `Review=deny` condition is not explained by a small aggregate fluctuation. The paired outcomes are strongly asymmetric: substantially more tasks changed from success under baseline to failure under Flight Recorder than changed in the opposite direction.

This analysis does not alter the primary security result and does not redefine the confirmatory condition. The post-hoc `Review=approve` sensitivity remains separate evidence and cannot replace `Review=deny` in the v2 result.
