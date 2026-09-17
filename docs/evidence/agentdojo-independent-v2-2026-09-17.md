# AgentDojo independent evaluation v2 — frozen evidence

**Frozen:** 2026-09-17

## Status

This document freezes the outcome of the independent evaluation defined before v2 outcome collection in `paper/independent-evaluation-protocol-v2.md`. The Agent Flight Recorder policy was not tuned against v2 cases before this result was recorded.

The first workflow attempt, run `35180104833`, failed during pre-execution protocol testing because the new manifest parser did not recognize the existing `userTask` / `injectionTask` field names. No v2 manifest was generated and no v2 model evaluation ran in that attempt. The parser-only infrastructure correction was committed before the successful execution.

## Provenance

- Protocol commit: `f2ea33d8da9d45fc0c7b66969ef696eb15f5cce5`
- Deterministic generator/test commit: `b0e586d550340665b9def0ee9b972a0765cae5bf`
- Parser corrections: `c1a02231d8b892bb512cc87357bd35079c729ea9`, `ea13b0007def03efcbd46b22734d91485678646a`
- Successful workflow commit: `9ef3022fa5dd05ae8746c6f8b4556ad6311e30a5`
- GitHub Actions run: `35180860582`
- Artifact: `agentdojo-v2-35180860582`
- Artifact SHA-256 reported by GitHub: `3a4e8c97a8237b8f2fa5eae08f9fc2e4188c72173ff594a58680b7b907faac81`
- Generated manifest SHA-256: `133014deda3d84607e29270525fce26e45b3f75b2b4f94559135c373f4b1b3aa`
- AgentDojo: `0.1.35`, benchmark `v1.2.2`
- Suite: `workspace`
- Attack: `tool_knowledge`
- Confirmatory review policy: `deny`
- Pair count: 120 unique selected pairs
- Azure deployment identifier: `gpt-4.1-mini-agent-flight-decoder`

All workflow gates passed in the successful run: repository regression tests, AgentDojo adapter tests, v2 protocol/overlap tests, Azure configuration validation, deterministic manifest generation, manifest conversion, all 120 paired evaluations, paired analysis, provenance checksums, and artifact upload.

## Frozen primary results

| Metric | Baseline | Agent Flight Recorder |
| --- | ---: | ---: |
| Attack success | 20/120 (16.7%) | 0/120 (0.0%) |
| Attack resisted | 100/120 (83.3%) | 120/120 (100.0%) |
| Utility success | 61/120 (50.8%) | 35/120 (29.2%) |

Attack-success Wilson 95% confidence intervals:

- Baseline: 11.1% to 24.3%
- Agent Flight Recorder: 0.0% to 3.1%

Observed attack-risk difference, Flight Recorder minus baseline: **-16.7 percentage points**.

Observed relative attack reduction: **100%**. This is a finite-sample ratio and must not be interpreted as proof of complete security or a zero population attack rate.

Paired attack discordance:

- baseline attack succeeded / Flight Recorder resisted: 20
- baseline resisted / Flight Recorder attack succeeded: 0

Exact two-sided McNemar p-value for attack success: **1.90735e-06**.

Under the recorded benchmark, model, attack, tool, metadata, and frozen-policy conditions, the paired v2 result provides strong evidence that Agent Flight Recorder reduced observed attack success relative to baseline.

## Utility tradeoff

Legitimate-task utility was **61/120 (50.8%)** for baseline and **35/120 (29.2%)** for Flight Recorder under the confirmatory `Review=deny` condition. The observed difference is **-21.7 percentage points**.

This cost is material. The security result must not be presented as preserving baseline utility. Earlier post-hoc Review sensitivity and repeated-trial evidence indicated that review handling accounts for much of the utility loss, but those analyses do not redefine this confirmatory result and do not authorize changing the frozen v2 condition after outcomes were seen.

## Relationship to earlier evidence

The first preregistered 30-pair holdout recorded 2/30 baseline attack successes versus 0/30 for Flight Recorder, with an exact McNemar p-value of 0.5. Its attack endpoint was underpowered. V2 increased the number of unique paired opportunities and recorded 20 baseline-only attack successes versus zero Flight Recorder attack successes.

The repeated-trials study reused known holdout identities and therefore remains stochastic-variance evidence rather than additional independent confirmatory units. It must not be pooled with v2 as if all observations were independent.

## Interpretation and claim boundary

Supported statement:

> In a preregistered 120-pair AgentDojo workspace evaluation using the recorded model, tool-knowledge attack, tool environment, metadata, and frozen Review=deny policy, Agent Flight Recorder recorded 0/120 attack successes versus 20/120 for the paired baseline (exact two-sided McNemar p=1.91e-06). Legitimate-task utility was lower with Flight Recorder, 35/120 versus 61/120, demonstrating a substantial security-utility tradeoff under this review policy.

Do not describe this experiment as proving that Agent Flight Recorder is universally secure, prevents all prompt injection, has a zero attack-success probability, or preserves utility. Do not use the post-hoc `Review=approve` findings to replace the confirmatory `Review=deny` result.

## Research-cycle stopping decision

This v2 result closes the planned AgentDojo confirmatory research cycle. No v3 evaluation should be initiated merely to improve, tune, or replace these observed outcomes. New experiments are justified only by a separately motivated research question or a concrete external-review requirement, with a new protocol frozen before outcome collection.
