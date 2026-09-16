# AgentDojo preregistered 30-pair holdout — 2026-09-16

## Status

This document freezes the first confirmatory holdout defined under `paper/experiment-protocol-v1.md`. No Agent Flight Recorder policy change was made after holdout execution began and before these outcomes were recorded.

## Protocol and selection

- Protocol commit: `5f1b066eaefa58183a86fd25258ac94c3d4f858e`
- Holdout manifest commit: `f70fe79d99249259502269a103b6af6a47fb3a33`
- Holdout runner/overlap enforcement: `9043df1086509ae5c80dbec531b4fd5a3c86cd2d`
- Holdout protocol tests: `654276c065eb5d06fdabbfa79888b838f3dbb381`
- Workflow run commit: `8e0d879f90afecd23f282919bb9f99ae41a531f5`
- AgentDojo: `0.1.35`, benchmark `v1.2.2`
- Suite: `workspace`
- Attack: `tool_knowledge`
- Review policy: `deny`
- Pair count: 30
- Holdout injection objectives: `injection_task_10` through `injection_task_13`
- Diagnostic manifest overlap: 0 pairs

The prior 30-pair diagnostic manifest used injection tasks 0 through 9. The confirmatory holdout reused the comparable `user_task_0` through `user_task_29` distribution but paired them with injection tasks 10 through 13, which had not appeared in the frozen diagnostic set. Pair identities were committed before any holdout model calls.

The earlier 9-pair draft holdout manifest was never executed. It was superseded before holdout model calls so the sample matched protocol v1's declared 30-pair design.

## Run provenance

- GitHub Actions run: `35162167755`
- Workflow: `AgentDojo preregistered holdout`
- Artifact: `agentdojo-holdout-35162167755`
- Artifact SHA-256 reported by GitHub: `a1e4e2cc246496621ebcb2c7afbdb88019fa63ef6b85bca99298a4782debe63a`
- Holdout manifest SHA-256 recorded by the run: `ac4a675b79dbd39ee84e5fa2c775ad412bee4d79a8ce524d235c7adfa1416c41`
- Frozen diagnostic manifest SHA-256 recorded by the run: `23bada88bfaf79b652e683cf351deaac25046a42324c385304d8145ea390cc38`
- AgentDojo user tasks visible to the pinned suite: 40
- AgentDojo injection tasks visible to the pinned suite: 14
- Azure deployment identifier recorded by the workflow: `gpt-4.1-mini-agent-flight-decoder`

## Confirmatory results

| Metric | Baseline | Agent Flight Recorder |
| --- | ---: | ---: |
| Attack success | 2/30 (6.7%) | 0/30 (0.0%) |
| Attack resisted | 28/30 (93.3%) | 30/30 (100.0%) |
| Utility success | 20/30 (66.7%) | 15/30 (50.0%) |

Attack-success Wilson 95% confidence intervals:

- Baseline: 1.8% to 21.3%
- Agent Flight Recorder: 0.0% to 11.4%

Observed attack-risk difference, Flight Recorder minus baseline: **-6.7 percentage points**.

Observed relative attack reduction: **100%**, but this ratio is based on only two baseline attack successes and must not be treated as a precise effect estimate.

Paired attack discordance:

- baseline attack succeeded / Flight Recorder resisted: 2
- baseline resisted / Flight Recorder attack succeeded: 0
- both attack succeeded: 0
- both resisted: 28

Exact two-sided McNemar p-value for attack success: **0.5**.

The primary paired comparison therefore does **not** establish a statistically significant reduction in attack success at a conventional 0.05 threshold. The holdout direction is consistent with the diagnostic result, and no holdout attack succeeded against Flight Recorder, but the baseline attack-success rate was low and the sample provides little statistical power.

## Utility tradeoff

Utility success was 20/30 for baseline and 15/30 for Flight Recorder.

Paired utility outcomes:

- both succeeded: 15
- baseline succeeded / Flight Recorder failed: 5
- baseline failed / Flight Recorder succeeded: 0
- both failed: 10

The exact two-sided McNemar p-value for the 5-to-0 utility discordance is **0.0625**. This does not cross a conventional 0.05 threshold, but the observed 16.7 percentage-point utility decrease is large enough that it must be treated as a real engineering concern rather than described as preserved utility.

No policy changes are made in response to this result before the result is frozen.

## Interpretation

The holdout supports three narrow factual observations under the recorded conditions:

1. no injection objective succeeded against Agent Flight Recorder in these 30 preregistered holdout pairs;
2. two injection objectives succeeded against the paired baseline;
3. Flight Recorder completed five fewer legitimate tasks than baseline in the paired holdout.

The experiment does **not** confirm the primary hypothesis with strong statistical evidence. The attack endpoint is underpowered because only two baseline cases were vulnerable. The utility result also prevents a claim that the security result came without a material task-completion cost.

## Claim boundary

Do not describe this result as "100% secure," "zero attack rate," or proof that Agent Flight Recorder prevents prompt injection generally.

A defensible description is:

> In a preregistered 30-pair AgentDojo holdout using four injection objectives absent from the diagnostic set, Agent Flight Recorder recorded 0/30 attack successes versus 2/30 for baseline. The paired attack difference was not statistically significant (exact McNemar p=0.5), and Flight Recorder utility was lower (15/30 versus 20/30), so larger evaluation is required before drawing a strong effectiveness conclusion.

## Next experimental implication

The policy remains frozen. The next experiment, if performed, should increase the number of independent attack opportunities without selecting or tuning cases based on Flight Recorder outcomes. It should be designed before execution and should measure both attack reduction and the utility cost explicitly.
