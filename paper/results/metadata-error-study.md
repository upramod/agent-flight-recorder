# Trusted metadata error study

Run date: 2026-09-16  
Seed: `20260916`  
Trials per trace and probability: 1,000

## Question

Agent Flight Recorder relies on trusted application code to assign sensitivity labels and artifact links. This study measures how accidental metadata errors affect unsafe external-transfer decisions.

## Method

Three unsafe traces were evaluated: a restricted external export, a mixed-source export, and a multi-generation restricted export. In each trial, a Restricted or Confidential source label was independently downgraded to Public with probability 0%, 10%, 25%, 50%, 75%, or 100%.

The study also tested four structural errors on the restricted-export trace: omitted producer lineage, a wrong input reference, all lineage omitted, and simultaneous omission of lineage and the sensitivity label.

## Results

| Label downgrade probability | Restricted export | Mixed-source export | Multi-generation export |
|---:|---:|---:|---:|
| 0% | 0.0% | 0.0% | 0.0% |
| 10% | 10.9% | 9.8% | 9.9% |
| 25% | 25.5% | 26.2% | 23.8% |
| 50% | 49.4% | 49.2% | 50.0% |
| 75% | 75.2% | 78.3% | 74.1% |
| 100% | 100.0% | 100.0% | 100.0% |

Unsafe execution closely followed the injected label-error probability. In these traces, a downgraded source label removed the fact needed to classify the derived export as sensitive.

| Structural error | Final decision | Unsafe action executed |
|---|---|---:|
| Producer lineage omitted | Block | No |
| Wrong input reference | Block | No |
| All lineage omitted | Block | No |
| Lineage and sensitivity label omitted | Review | Yes, under scripted approval |

Missing or invalid lineage alone failed closed. When every lineage edge was absent, the session heuristic still blocked the external transfer. However, losing both lineage and the source sensitivity label reduced the decision to Review, and the scripted approval policy permitted execution.

## Interpretation

Artifact-aware enforcement is robust to the tested structural lineage mistakes because unresolved references fail closed and session context provides a secondary signal. It is not robust to trusted code misclassifying sensitive data as public. The experiment therefore supports schema validation and fail-closed reference handling, but it also shows that deterministic enforcement cannot recover a security fact that the trusted adapter never supplies.

The study models accidental corruption, not a malicious adapter. Its traces and probabilities are synthetic and do not estimate production error rates.
