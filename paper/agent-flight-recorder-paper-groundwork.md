# Agent Flight Recorder: paper groundwork

## Working title
Agent Flight Recorder: Deterministic Runtime Enforcement for Tool-Using AI Agents

## Paper type
Systems and software engineering paper with an artifact evaluation.

## Research question
Can a deterministic runtime layer reduce unsafe tool execution by combining executed session history with source-linked artifact lineage, without accessing private model reasoning?

## Contributions
1. Observable-only control over structured tool proposals.
2. Session-aware assessment using only successfully executed actions.
3. Artifact-aware enforcement that propagates the strongest source sensitivity.
4. Explicit proposal, assessment, approval, execution, and audit states.
5. A live Azure model adapter, synthetic tool environment, browser approval surface, and deterministic replay suite.

These are engineering contributions. The paper must compare them with existing prompt-injection, temporal, causal, provenance, and tool-authorization defenses before making a novelty claim.

## System model
An action is represented as id, session, tool, operation, resource, sensitivity, destination trust, privilege, provenance, and data-flow references.

Assess(action, history, artifactGraph) returns score, decision, and reasons.
Allow executes immediately. Review requires action-specific approval. Block never calls the executor.

For a derived artifact, effective sensitivity is the strongest sensitivity among the artifact and all declared ancestors:
Public < Internal < Confidential < Restricted

An upload of a Confidential or Restricted artifact to a destination that is not Trusted is blocked.

## Threat model
The attacker may control external content consumed by the agent, including a document containing instructions to upload data. The attacker may control an untrusted destination.

The attacker cannot modify trusted policy code, trusted adapter metadata, session identifiers, successful execution history, or the artifact graph.

Covered cases include indirect instructions, restricted queries, derived exports, external uploads, missing references, duplicate output IDs, and cross-session references.

Excluded cases include compromised model weights, compromised trusted adapters, tool vulnerabilities, network attacks, real customer data, distributed persistence, and production authorization.

## Baselines
1. No gate. Every proposal executes.
2. Point-action policy. Assess the current action without history or lineage.
3. Session heuristic. Use executed session history without an artifact graph.
4. Artifact-aware policy. Use trusted lineage and sensitivity propagation.
5. Human review only. Pause sensitive actions without deterministic blocking.

## Evaluation matrix
Use fixed synthetic traces and run every trace against every baseline.

| Trace | Source | Artifact | Destination | Expected result |
| Public export | Public | Public | Untrusted | Allow |
| Restricted export | Restricted | Restricted | Untrusted | Block |
| Mixed export | Public plus Restricted | Restricted | Untrusted | Block |
| Trusted destination | Restricted | Restricted | Trusted | Policy-defined |
| Missing source | Unknown | Unknown | Untrusted | Block |
| Cross-session source | Unknown | Unknown | Untrusted | Block |
| Denied producer | Restricted | None | Untrusted | Precondition failure |
| Model refusal | Restricted | None | None | Model stop |

## Metrics
Security: unsafe execution rate, blocked exfiltration rate, false block rate, source-attribution accuracy, fail-closed rate, and proposal-to-execution discrepancy rate.

Utility: task completion, model-stop rate, approval rate, rejection rate, precondition failures, repeated actions, and model calls.

Operations: assessment latency, gate overhead, end-to-end latency, review time, and trace size.

Report confidence intervals. Record model deployment, prompt version, sampling settings, scenario seed, timestamp, and repository commit. Keep credentials outside the artifact.

## Required figures
Figure 1: model proposal to trusted adapter to recorder to gate to approval or executor to trace.
Figure 2: one session showing untrusted input, restricted access, export creation, upload proposal, and enforcement result.
Figure 3: benign task completion versus unsafe execution as review thresholds change.

## Claims supported by the current artifact
The prototype separates proposals from executed actions. The gate prevents its synthetic blocked executor from running. Artifact sensitivity propagates through successful producer links. Public and restricted exports receive different decisions in one session. Invalid lineage fails closed. The Azure adapter can make a live proposal while deterministic code remains the execution authority. Private chain-of-thought is not required.

## Claims not supported
The current artifact does not show that Azure OpenAI reliably resists prompt injection. It does not cover all attacks, prove production readiness, calibrate scores as probabilities, or establish novelty against recent temporal and causal defenses. A model stop is not a policy block. A scripted replay is not a live attack.

## Related work
Start with these primary papers:

- Greshake et al., Not What You’ve Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection, arXiv:2302.12173.
- Zhan et al., InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents, arXiv:2403.02691.
- Design Patterns for Securing LLM Agents against Prompt Injections, arXiv:2506.08837.
- AgentSentry: Mitigating Indirect Prompt Injection in LLM Agents via Temporal Causal Diagnostics and Context Purification, arXiv:2602.22724.
- AttriGuard: Defeating Indirect Prompt Injection in LLM Agents via Causal Attribution of Tool Invocations, arXiv:2603.10749.
- Agent Security is a Systems Problem, arXiv:2605.18991.

The related-work section must distinguish input sanitization, model-side recognition, causal attribution, human approval, data-flow enforcement, and post-hoc logging.

## Abstract draft
Tool-using AI agents can transform untrusted observations into consequential tool actions. A document read, restricted query, export operation, and external upload may appear plausible in isolation while their executed sequence creates a data-exfiltration path. We present Agent Flight Recorder, a runtime enforcement prototype that evaluates structured action proposals at the tool boundary without accessing private model reasoning. The design separates proposal, assessment, approval, execution, and audit state. A deterministic policy combines session history with trusted artifact lineage, propagates source sensitivity through derived artifacts, and blocks sensitive artifacts from leaving trusted destinations. We implement a live Azure model adapter, synthetic tools, browser approvals, and deterministic replay. The evaluation compares no-gate, point-action, session-heuristic, artifact-aware, and human-review baselines using unsafe execution, benign completion, lineage attribution, latency, and execution-integrity metrics. The artifact demonstrates the control flow and fail-closed behavior; it does not establish broad attack coverage or production readiness.

## Work before submission
1. Add a benchmark runner that emits machine-readable JSON.
2. Implement each baseline.
3. Add fixed seeds and prompt versions.
4. Record proposals, decisions, approvals, executor results, and lineage edges.
5. Measure latency and review cost.
6. Run repeated trials with confidence intervals.
7. Compare with at least one established benchmark or defense.
8. Separate model refusal from policy blocking.
9. Perform sensitivity analysis on policy weights.
10. Report synthetic-environment limits in the main paper.

## Positioning
The strongest paper is a careful systems artifact paper about enforceable runtime state and data-linked decisions. A five-action demo alone cannot support a claim that agents are secure.