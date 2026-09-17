# Agent Flight Recorder repeated-trials protocol v1

**Frozen:** 2026-09-16

## Purpose

Estimate run-to-run variation in AgentDojo attack success and legitimate-task utility before making stronger claims about Agent Flight Recorder. The preregistered holdout and the later Review=approve sensitivity run produced materially different baseline outcomes on the same pair identities. A repeated design is therefore required.

## Status of prior evidence

The original preregistered holdout remains the primary confirmatory result. This repeated-trials study is a new experiment and does not replace it.

The Review=approve result remains post-hoc sensitivity evidence.

No policy code, score threshold, trust mapping, provenance rule, or tool mapping may change during this repeated-trials experiment.

## Experimental conditions

Use the frozen 30-pair holdout manifest at `integrations/agentdojo/holdout-manifest.json`.

Evaluate three conditions:

1. `baseline`;
2. Agent Flight Recorder with `Review=deny`;
3. Agent Flight Recorder with `Review=approve`.

Each condition is evaluated for **5 independent repetitions** of all 30 pairs, producing 150 case observations per condition and 450 condition-case observations total.

The repetition count is fixed before execution. Failed infrastructure runs may be retried only when no valid result was produced. Valid unfavorable runs may not be discarded.

## Blocking and execution order

Each repetition is a block. Within every block, all three conditions use the same 30 pair identities.

Condition order rotates by block to reduce systematic time/order effects:

- block 1: baseline, deny, approve;
- block 2: deny, approve, baseline;
- block 3: approve, baseline, deny;
- block 4: baseline, approve, deny;
- block 5: deny, baseline, approve.

The benchmark runner starts a fresh AgentDojo execution for every condition/pair observation. No policy history is shared across observations.

## Fixed configuration

- AgentDojo `v1.2.2`;
- workspace suite;
- `tool_knowledge` attack;
- same Azure deployment and API configuration used by the existing evidence workflow;
- trusted email domain `bluesparrowtech.com`;
- same system prompt;
- same tool catalog;
- same Flight Recorder policy code and thresholds.

## Outcomes

For each condition and block record:

- attack successes out of 30;
- utility successes out of 30;
- Allow, Review, Block, executed, and denied action counts where applicable.

Across five blocks report:

- total attack successes out of 150;
- total utility successes out of 150;
- block-level mean, minimum, maximum, and sample standard deviation for attack-success proportion;
- block-level mean, minimum, maximum, and sample standard deviation for utility proportion;
- raw block results without suppressing outliers.

Pair-level repeated outcomes must remain available in the artifact.

## Analysis boundary

This study estimates observed variation under one benchmark/model/configuration. Repeated observations are not independent in the same sense as newly sampled benchmark tasks, because pair identities repeat. Aggregate 150-case proportions must therefore not be presented as if they were 150 independently sampled tasks.

Comparisons between deny and approve are descriptive sensitivity comparisons unless a later analysis plan justifies a paired repeated-measures model. The experiment is not permission to tune the policy after each block.

## Stopping rule

Run exactly five valid blocks. Do not stop early because results look favorable or unfavorable.

## Evidence

Every block must preserve raw console output, AgentDojo logs, Flight Recorder policy logs, commit SHA, GitHub Actions run metadata, and file checksums. A final aggregate file must be generated from the raw block outputs rather than manually entered totals.

## Claim boundary

The study may support statements about observed run-to-run stability or variability under the fixed conditions. It cannot establish universal attack rates, universal security, or performance on other models, attacks, suites, or production systems.
