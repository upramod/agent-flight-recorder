# Agent Flight Recorder paper preparation plan

**Prepared:** 2026-09-17

## Paper decision

Prepare the manuscript. The evidence now supports a narrow, publishable benchmark claim: trajectory-aware runtime enforcement reduced observed AgentDojo prompt-injection success under the frozen experimental conditions. The manuscript must treat the utility penalty as a primary result rather than a footnote.

## Working title

**Agent Flight Recorder: Trajectory-Aware Runtime Enforcement for Tool-Using AI Agents**

## Central research claim

In a preregistered 120-pair AgentDojo workspace evaluation, the frozen Agent Flight Recorder condition recorded 0/120 attack successes compared with 20/120 for the paired baseline. Exact paired testing yielded McNemar p=1.91e-06. Under the same confirmatory `Review=deny` condition, legitimate-task utility fell from 61/120 to 35/120.

The contribution is therefore not “security without cost.” The result is evidence that trajectory-aware enforcement can sharply reduce observed attack completion while creating a measurable intervention cost that depends on review handling.

## Evidence hierarchy

1. **Primary confirmatory evidence:** independent v2, 120 unique paired opportunities, frozen before outcome collection.
2. **Earlier confirmatory evidence:** preregistered 30-pair holdout, directionally consistent but underpowered.
3. **Diagnostic evidence:** original 30-pair development benchmark. Use for engineering history, not confirmatory inference.
4. **Post-hoc robustness evidence:** Review=approve sensitivity and repeated stochastic trials. Use to analyze the utility mechanism. Do not merge with the confirmatory endpoint or present as preregistered.

## Manuscript structure

### 1. Introduction

Define the failure mode: tool-using agents can accumulate risk across a trajectory even when individual actions appear locally acceptable. State the runtime-enforcement question and the need to evaluate both attack completion and legitimate-task utility.

### 2. System design

Describe the policy gate, trajectory history, provenance, destination trust, sensitivity, privilege, and artifact-lineage signals. Separate model reasoning from externally observable actions and policy metadata. Do not claim access to private chain-of-thought.

### 3. Experimental method

Document AgentDojo 0.1.35 / benchmark v1.2.2, workspace suite, tool_knowledge attack, paired baseline design, Azure deployment identifier, frozen Review=deny policy, deterministic manifest selection, overlap exclusion, stopping rule, and exact paired analysis.

### 4. Primary results

Lead with raw paired counts. Report 20/120 versus 0/120 attack success, Wilson intervals, -16.7 percentage-point observed risk difference, and exact McNemar p=1.91e-06.

### 5. Utility and review behavior

Report 61/120 versus 35/120 utility under Review=deny. Present the post-hoc Review=approve evidence only as mechanism/sensitivity analysis, clearly labeled after-the-fact. Explain that review semantics, not only detection quality, determine operational utility.

### 6. Threats to validity

Cover benchmark scope, one principal model deployment, one primary attack family, metadata correctness, tool-mapping assumptions, model nondeterminism, finite sample size, and the fact that AgentDojo evaluator success is not equivalent to all forms of compromise.

### 7. Related work

Position the work against prompt-injection defenses, agent/tool authorization, information-flow/provenance controls, runtime policy enforcement, and agent evaluation benchmarks. Perform a fresh literature search before drafting this section. Do not manufacture novelty claims from memory.

### 8. Discussion

Frame the engineering result as a security-utility frontier. Explain why a strict non-interactive review policy protects more aggressively but blocks legitimate workflows, while post-hoc sensitivity suggests that an approval channel may recover utility. Keep confirmatory and post-hoc evidence separate.

### 9. Conclusion

State only the benchmark-specific result and the design implication: trajectory-aware enforcement warrants further study, while review handling is part of the security mechanism and cannot be ignored when measuring usefulness.

## Figures and tables to prepare

- Architecture diagram of agent → policy gate → tool execution → audit/provenance path.
- Experimental-flow diagram showing manifest freeze, paired execution, evaluator, and evidence artifact.
- Primary paired attack-results table.
- Utility-results table with confirmatory and post-hoc conditions clearly separated.
- Optional policy-decision distribution figure if raw audit logs support it without selective reporting.

## Writing constraints

Report AI assistance truthfully under the target venue's policy. Keep code, protocol, raw evidence, and manuscript claims traceable to repository commits. Avoid universal-security language. Do not call 0/120 a zero attack rate outside the observed sample. Do not hide the utility loss. Do not tune the frozen policy against v2 cases and then present a new result as confirmatory.

## Immediate preparation sequence

1. Freeze v2 evidence in `docs/evidence`.
2. Preserve the successful workflow artifact and hashes.
3. Build the paper's results tables directly from frozen evidence.
4. Conduct a fresh related-work search and build a citation matrix.
5. Draft Methods and Results before Introduction or Discussion.
6. Draft the full manuscript around the narrow claim boundary.
7. Run an internal claim-to-evidence audit before submission.
