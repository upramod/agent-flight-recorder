# Agent Flight Recorder repeated stochastic evaluation protocol v1

**Frozen:** 2026-09-16

## Purpose

This is a post-hoc variance study. It does not replace the preregistered 30-pair holdout result.

The study estimates run-to-run variation for the already-seen 30-pair holdout under three fixed execution conditions:

1. baseline agent;
2. Agent Flight Recorder with `Review=deny`;
3. Agent Flight Recorder with `Review=approve`.

No policy code, score threshold, trusted-domain rule, tool mapping, attack family, benchmark pair, or model deployment is changed for this study.

## Research questions

1. How much do attack-success and legitimate-task utility rates vary across independent reruns of the same AgentDojo cases with the same model deployment?
2. Does the observed utility difference between `Review=deny` and `Review=approve` persist across reruns?
3. Does either Flight Recorder Review handling mode repeatedly show attack successes on these cases?

These questions are descriptive and exploratory because the pair identities have already been observed.

## Fixed cases

Use the 30 pair identities in `integrations/agentdojo/holdout-manifest.json`.

The diagnostic manifest remains excluded from overlap checks. The holdout pairs must not be edited during this study.

## Repetitions

Run **five complete independent repetitions**.

Each repetition executes every holdout pair once under each of the three conditions, producing 90 benchmark executions per repetition and 450 benchmark executions in total.

The same Azure deployment and AgentDojo v1.2.2 workspace suite are used throughout.

## Condition order

To reduce a fixed within-pair ordering effect, the condition order rotates by repetition:

- repetition 1: baseline, deny, approve
- repetition 2: deny, approve, baseline
- repetition 3: approve, baseline, deny
- repetition 4: baseline, approve, deny
- repetition 5: deny, baseline, approve

The order is declared here before these repeated runs are inspected.

## Metrics

For every pair, condition, and repetition record:

- utility success;
- attack success;
- attack resistance;
- raw console output;
- Flight Recorder audit output when present.

For each condition report per-repetition counts and rates, plus across-repetition mean, sample standard deviation, minimum, and maximum for utility and attack-success rates.

Also report per-repetition differences against baseline and the utility difference between `Review=approve` and `Review=deny`.

## Interpretation rules

- Do not pool 150 repeated observations per condition and describe them as 150 independent benchmark tasks. The same 30 pair identities are repeated five times.
- Do not present this study as a new holdout or confirmatory test.
- Zero observed attacks in any condition does not imply a zero underlying attack probability.
- Differences between `Review=deny` and `Review=approve` are sensitivity evidence, not a basis for silently changing the frozen policy.
- If a run fails for infrastructure reasons, rerun that repetition only and record the rerun attempt. Do not remove unfavorable cases.
- No policy tuning is allowed during the five-repetition study.

## Evidence boundary

A permitted conclusion is of the form:

> Across five repeated executions of the same 30 already-seen AgentDojo holdout pairs, observed attack-success and utility rates varied by the recorded amounts under baseline, Review=deny, and Review=approve conditions.

This study cannot establish general security or provide an independent confirmatory estimate of performance on unseen tasks.
