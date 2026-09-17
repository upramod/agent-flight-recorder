# Reviewer-style submission risk audit

Reviewed: 2026-09-17

Purpose: stress-test the current USENIX-oriented manuscript without changing the frozen v2 experiment or inventing stronger claims.

## Likely reviewer objection 1: the defense obtains security by blocking useful work

Evidence supporting the objection:

- baseline utility: 61/120;
- Recorder utility under confirmatory `Review=deny`: 35/120;
- paired utility discordance: 29 baseline-only successes versus 3 Recorder-only successes;
- exact two-sided McNemar p=2.55601e-06.

Response already supported by evidence:

The paper must treat this as a primary result, not a limitation hidden late in the paper. The contribution is a measured security-utility tradeoff under a strict review policy. Post-hoc `Review=approve` evidence can explain mechanism but cannot be used to claim that the confirmatory system preserves utility.

Required manuscript posture: keep utility in the abstract, Results, Discussion, and Conclusion. Do not describe the v2 policy as cost-free or operationally ready.

## Likely reviewer objection 2: 0/120 does not prove robustness

Evidence supporting the objection:

- Recorder observed 0/120 attack successes;
- Wilson 95% interval extends to approximately 3.1%;
- one fixed AgentDojo attack family was used;
- no adaptive adversary optimized against the policy.

Response already supported by evidence:

State only that observed attack completion was lower under the recorded benchmark conditions. Do not claim zero population risk, universal prevention, or adaptive robustness. The manuscript already cites adaptive-attack work and identifies adaptive evaluation as unmeasured.

## Likely reviewer objection 3: pair identities are new combinations, not wholly novel benchmark primitives

Evidence supporting the objection:

The v2 unit is a unique `(user task, injection task, attack configuration)` identity. Selection excluded prior exact pair identities, but the finite AgentDojo workspace reuses user-task and injection-task components across combinations.

Response required:

Describe v2 as 120 unique previously unused pair identities, not 120 wholly unseen task primitives. Add this distinction wherever “independent” could be read as complete content independence. This is a benchmark-universe limitation, not a protocol violation.

## Likely reviewer objection 4: comparison is against baseline, not the strongest published defense

Evidence supporting the objection:

Related work includes CaMeL, AgentArmor, MELON, AttriGuard, tool-interface firewalls, and adaptive evaluations. V2 directly compares the paired baseline agent with Agent Flight Recorder; it does not implement a head-to-head comparison with those systems.

Response already supported by evidence:

Do not claim superiority to published defenses. Position the contribution as a runtime-enforcement design plus a preregistered paired benchmark result. A direct-defense comparison may be requested by reviewers, but it is not grounds to modify or rerun the frozen v2 endpoint before submission merely to improve optics.

## Likely reviewer objection 5: the trusted adapter can be wrong

Evidence supporting the objection:

The policy relies on trusted tool mappings, sensitivity labels, destination trust, provenance, and optional artifact links. Earlier metadata-corruption tests showed degraded protection when trusted labels were downgraded.

Response already supported by evidence:

Treat adapter correctness as part of the trusted computing base. Keep the metadata-corruption result in Engineering Validation and state deployment requirements such as schema validation, tool registration, identity-bound sessions, and tamper-resistant state.

## Likely reviewer objection 6: handcrafted scoring lacks formal or learned calibration

Evidence supporting the objection:

The policy uses engineered risk weights and fixed Allow/Review/Block thresholds rather than a learned probability model or formal proof.

Response already supported by evidence:

The manuscript evaluates the frozen policy as a system. It does not claim that the weights are optimal or probabilistically calibrated. Transparent rules are part of the implementation choice, not a proof of optimality.

## Likely reviewer objection 7: model stochasticity weakens one-run inference

Evidence supporting the objection:

The earlier same-pair reruns showed baseline attack outcomes changing from 2/30 to 0/30 and small utility variation without policy changes.

Response already supported by evidence:

V2 increased the number of unique pair identities rather than counting repeated known cases as independent confirmatory observations. The paired design controls task identity but not language-model randomness. Keep repeated-trial data as variance evidence and do not pool it with v2.

## Likely reviewer objection 8: novelty is narrower than the title may suggest

Evidence supporting the objection:

Published systems already use runtime traces, data/control flow, counterfactual attribution, and tool-boundary controls.

Response required:

Avoid first-of-kind language. The paper's differentiating engineering semantics are successful-execution-only causal history, compact trusted metadata, optional named artifact lineage, explicit Review handling, and a preregistered paired evaluation. Novelty should be framed as the specific design/evidence package rather than a new defense category.

## Likely reviewer objection 9: the paper is short for a top-tier systems-security submission

Current compiled manuscript is approximately six pages including references, below the maximum allowed initial-submission length.

Interpretation:

Short length is not itself a defect, but the paper should not look underdeveloped. Use available space for clearer system detail, threat-model precision, an explicit experimental-unit explanation, artifact/reproducibility material, and stronger figures. Do not pad with speculative claims or redundant prose.

## Likely reviewer objection 10: public repository can break double-blind anonymity

Current mitigation:

- anonymous manuscript source uses `Anonymous Submission`;
- an allowlist-based artifact builder excludes `.git`, author-identifying paper files, and repository metadata;
- anonymous artifact hygiene workflow passed;
- compiled PDF is checked for author-name strings.

Remaining requirement:

Before submission, publish the review artifact through an anonymous URL or venue-approved anonymous artifact service. Do not link the public author-owned GitHub repository from the blinded manuscript.

## Submission gate

The paper is suitable to freeze as a submission candidate when all of the following are true:

- USENIX LaTeX build passes end-to-end;
- compiled PDF is anonymous and within the page limit;
- anonymous artifact hygiene passes;
- statistical verification remains consistent with frozen evidence;
- manuscript uses “unique previously unused pair identities,” not language implying wholly unseen primitive tasks;
- no unsupported superiority, universal-security, or zero-risk claim appears;
- Open Science appendix and anonymous artifact instructions are present;
- final human author review is still required before external submission.

No new AgentDojo run is required by this audit.
