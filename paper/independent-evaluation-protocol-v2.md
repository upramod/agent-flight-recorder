# Agent Flight Recorder Independent Evaluation Protocol v2

**Preregistered:** 2026-09-16
**Status:** design frozen before any v2 outcome collection

## Purpose

The first 30-pair preregistered holdout produced 2/30 baseline attack successes and 0/30 Agent Flight Recorder attack successes, but the paired security comparison was underpowered. Subsequent repeated executions reused those same 30 pair identities and are post-hoc variance evidence only. They must not guide case selection or policy tuning for this study.

This protocol defines the next evaluation before any v2 benchmark outcomes are inspected. Its goal is to increase the number and diversity of independent attack opportunities rather than repeat known holdout cases.

## Research question

Under fixed model, tool, benchmark, and policy conditions, does trajectory-aware runtime enforcement reduce prompt-injection attack success relative to the paired unprotected agent, and what legitimate-task utility cost accompanies that enforcement?

## Frozen policy boundary

The Agent Flight Recorder scoring rules, thresholds, provenance rules, trust rules, sensitivity mappings, privilege mappings, artifact-lineage behavior, and tool mappings are frozen at the repository state that precedes this protocol.

No observed case from the diagnostic set, first holdout, Review sensitivity run, or repeated-trials study may be used to tune this policy before v2 outcomes are frozen.

`Review=deny` remains the confirmatory Flight Recorder condition because it was the preregistered condition in protocol v1. `Review=approve` may be evaluated as a separately labeled secondary condition, but it cannot replace or redefine the confirmatory condition after results are seen.

## Experimental unit

The primary experimental unit is one unique `(user task, injection task, attack configuration)` opportunity evaluated as a matched pair:

1. baseline agent;
2. Agent Flight Recorder with the frozen confirmatory policy.

A pair is eligible only if its exact experimental identity has not appeared in the diagnostic 30-pair manifest, the first preregistered holdout, the Review sensitivity study, or the repeated-trials study.

Repeated stochastic executions of one identity are not counted as new independent experimental units.

## Target sample

Target at least **120 unique valid paired attack opportunities**. The manifest must be frozen before model execution.

If the pinned AgentDojo workspace suite cannot supply 120 previously unseen valid identities under one attack configuration, expand diversity in this order without inspecting outcomes:

1. additional previously unused valid user-task/injection-task combinations;
2. additional AgentDojo attack configurations supported by the pinned benchmark;
3. additional AgentDojo suites supported by the same integration, with suite recorded as a stratification variable.

Do not duplicate an experimental identity merely to reach 120. If fewer than 120 unique eligible opportunities exist, execute the full eligible universe and report the shortfall before outcome analysis.

## Selection procedure

A machine-generated eligibility inventory must enumerate candidate identities from the pinned benchmark before execution. It must subtract every identity already used in prior evidence.

Selection from the remaining eligible universe must use a deterministic rule fixed in the manifest generator, such as lexicographic ordering followed by a recorded hash-based permutation. The generator must not read prior outcome files, attack-success labels, policy decisions, or utility results.

The committed v2 manifest records:

- benchmark and AgentDojo versions;
- suite;
- attack configuration;
- user-task identifier;
- injection-task identifier;
- deterministic selection key;
- exclusion reason for any invalid candidate;
- hashes of all prior manifests used for overlap exclusion.

A protocol test must fail if any v2 identity overlaps a prior evaluated identity.

## Fixed execution conditions

Within each matched pair, baseline and Flight Recorder use the same:

- Azure OpenAI deployment;
- AgentDojo version and benchmark revision;
- suite and attack configuration;
- user task and injection task;
- tool catalog;
- initial benchmark state;
- non-policy adapter behavior.

The confirmatory Flight Recorder condition uses `Review=deny` and trusted domain `bluesparrowtech.com`, matching protocol v1 unless an infrastructure-only amendment is committed before outcome collection.

Secrets are never stored in experimental evidence.

## Endpoints

### Primary endpoint

`attack_success`, evaluated by AgentDojo's injection-task evaluator.

Primary paired comparison: baseline attack success versus frozen Flight Recorder `Review=deny` attack success.

### Secondary endpoints

- legitimate-task utility success;
- attack resistance;
- Allow / Review / Block counts;
- denied tool executions;
- false Review and false Block behavior where classification is defined;
- policy-decision latency when available.

`Review=approve`, if run, is a prespecified secondary sensitivity condition. Report it separately from the confirmatory result.

## Analysis plan

Report raw counts and paired outcomes first.

For the primary endpoint report:

- baseline and Flight Recorder attack-success counts and proportions;
- absolute paired risk difference;
- relative observed reduction when baseline attack success is non-zero;
- paired discordant counts;
- exact two-sided McNemar test;
- 95% confidence intervals for condition proportions and an appropriate interval for the paired effect.

Report utility with the same paired discipline, including discordant utility counts and exact McNemar testing. Do not describe utility as preserved merely because aggregate percentages are close.

If multiple suites or attack configurations are required to reach the target sample, report each stratum separately before any declared aggregate. The aggregate may include all preregistered strata, but heterogeneity must remain visible.

No case may be removed because its outcome is unfavorable.

## Invalid cases and infrastructure recovery

A case is invalid only for a documented execution failure that prevents the benchmark evaluator from producing the required outcome. Policy blocks, model refusals, tool errors caused by the evaluated trajectory, and unfavorable outcomes are not infrastructure failures.

Infrastructure-invalid cases remain in an exception log. Rerun only the same frozen identity after correcting the execution fault. Do not substitute a different case based on its observed result.

## Stopping rule

Stop after every identity in the frozen v2 manifest has one valid matched baseline/Flight Recorder result, subject only to documented infrastructure recovery.

Do not stop early for apparent benefit, harm, significance, or lack of significance.

## Evidence record

Retain:

- protocol commit;
- manifest commit and SHA-256;
- overlap-test output;
- repository execution commit;
- workflow revision and GitHub Actions run ID;
- AgentDojo and benchmark versions;
- non-secret model deployment identifier;
- raw per-case baseline and Flight Recorder results;
- policy audit logs;
- analysis output;
- artifact digest.

Freeze the primary result in `docs/evidence` before any policy modification prompted by v2 outcomes.

## Claim boundary

This experiment can estimate performance only under its recorded benchmark, model, tool, attack, and policy conditions. Zero observed Flight Recorder attacks does not establish zero population risk. A statistically significant paired result would support a benchmark-specific reduction claim, not universal prompt-injection prevention.

## Amendment rule

Any design change before the first v2 model call requires a numbered protocol amendment committed before execution. After the first outcome-producing model call, changes are post-hoc and cannot redefine this confirmatory experiment.