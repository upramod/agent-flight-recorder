# AgentDojo preregistered holdout evidence

**Date:** 2026-09-16  
**Repository:** `upramod/agent-flight-recorder`  
**Protocol:** `paper/experiment-protocol-v1.md`  
**Protocol commit:** `5f1b066eaefa58183a86fd25258ac94c3d4f858e`  
**Holdout run commit:** `8e0d879f90afecd23f282919bb9f99ae41a531f5`  
**GitHub Actions run:** `35162167755`  
**Artifact:** `agentdojo-holdout-35162167755`  
**Artifact ID:** `10473877037`  
**Artifact digest:** `sha256:a1e4e2cc246496621ebcb2c7afbdb88019fa63ef6b85bca99298a4782debe63a`

## Frozen configuration

- AgentDojo package: `0.1.35`
- Benchmark version: `v1.2.2`
- Suite: `workspace`
- Attack: `tool_knowledge`
- Review policy: `deny`
- Trusted email domain: `bluesparrowtech.com`
- Azure deployment identifier: `gpt-4.1-mini-agent-flight-decoder`
- Pair count: 30
- Diagnostic/holdout pair overlap: 0
- Holdout manifest SHA-256: `ac4a675b79dbd39ee84e5fa2c775ad412bee4d79a8ce524d235c7adfa1416c41`
- Diagnostic manifest SHA-256: `23bada88bfaf79b652e683cf351deaac25046a42324c385304d8145ea390cc38`

The 30-pair holdout uses `user_task_0` through `user_task_29` with previously unused injection objectives `injection_task_10` through `injection_task_13`, assigned round-robin. The holdout manifest was fixed before model outcomes were inspected. The runner validated all task IDs against the pinned suite and rejected overlap with the diagnostic manifest before model calls.

An earlier nine-pair draft manifest was superseded before any holdout model calls so the confirmatory run matched protocol v1's declared 30-pair design.

## Primary holdout result

| Metric | Baseline | Agent Flight Recorder |
| --- | ---: | ---: |
| Attack success | 2/30 (6.7%) | 0/30 (0.0%) |
| Attack resisted | 28/30 (93.3%) | 30/30 (100.0%) |
| Utility success | 20/30 (66.7%) | 15/30 (50.0%) |

Attack-success Wilson 95% confidence intervals:

- Baseline: 1.8% to 21.3%
- Agent Flight Recorder: 0.0% to 11.4%

Observed absolute attack-risk difference, Flight Recorder minus baseline: **-6.7 percentage points**.

Observed relative reduction: **100%**, because the baseline produced two attack successes and Flight Recorder produced none. This is an observed finite-sample result, not an estimate of a universal reduction.

Paired attack discordance:

- baseline attack succeeded / Flight Recorder resisted: 2
- baseline resisted / Flight Recorder attack succeeded: 0
- both succeeded: 0
- both resisted: 28

Exact two-sided McNemar p-value for attack success: **0.5**.

## Utility result

Utility success was lower with Flight Recorder in this holdout: **15/30** versus **20/30** for baseline.

Paired utility outcomes:

- both succeeded: 15
- baseline succeeded / Flight Recorder failed: 5
- baseline failed / Flight Recorder succeeded: 0
- both failed: 10

This means the holdout does **not** support a claim that the observed security improvement came without a utility cost. The utility result must be carried forward as part of the evidence, not hidden or tuned away.

## Interpretation

The preregistered holdout reproduced the favorable attack-success direction seen in the diagnostic evaluation: zero observed Flight Recorder attack successes versus two baseline successes on these 30 unseen pair combinations.

The confirmatory attack comparison is statistically underpowered. With only two discordant attack pairs, the exact McNemar test does not provide strong evidence against the null hypothesis. Zero observed Flight Recorder successes also does not imply a zero population attack rate; the Wilson interval extends to 11.4%.

At the same time, legitimate-task utility fell from 66.7% to 50.0%. The primary hypothesis therefore receives **mixed support** under this run: the security direction is favorable, but the stated goal of preserving legitimate-task completion is not demonstrated.

No policy thresholds, scoring rules, metadata rules, trust rules, or tool mappings should be modified and then evaluated against this same holdout as if it were still unseen. Any correction motivated by these outcomes starts a new development cycle and requires a new evaluation set.

## Evidence boundary

Claims supported by this run are limited to the recorded AgentDojo v1.2.2 workspace configuration, model deployment, `tool_knowledge` attack, metadata mapping, and policy state.

A safe statement is:

> In a preregistered 30-pair AgentDojo holdout using previously unused injection objectives, the baseline completed 2 attack objectives while Agent Flight Recorder completed 0. The sample was too small for a statistically strong paired attack result, and Flight Recorder utility was lower (15/30 versus 20/30), so the experiment does not establish general prompt-injection prevention or cost-free security.

Do not describe this result as `100% secure`, universal prevention, or proof that Flight Recorder preserves utility.
