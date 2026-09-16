# Related-work comparison and positioning

Reviewed: 2026-09-16

## Direct conclusion

A broad novelty claim for "trajectory-aware runtime security" is not defensible. AgentArmor already converts agent runtime traces into program-dependence representations and checks security policies. CaMeL and RTBAS already constrain data and control flow around tool use. AgentSentry and AttriGuard already use temporal or causal analysis of tool trajectories.

Agent Flight Recorder should be positioned as a small, reproducible systems artifact that isolates four operational semantics:

1. only successful executions enter causal history;
2. derived artifacts inherit sensitivity from named source artifacts;
3. approval belongs to one pending action and expires;
4. model stop, human rejection, policy block, and executor failure remain distinct audit outcomes.

These features may form a useful engineering combination. They do not yet establish a new defense class.

## Comparison matrix

| Work | Primary purpose | Enforcement point | Uses trajectory | Uses data attribution | Deterministic execution block | Main distinction from Agent Flight Recorder |
|---|---|---|---|---|---|---|
| Greshake et al. (2023) | Establish indirect prompt-injection threat | Attack study | Multi-step examples | No formal artifact graph | No | Threat motivation |
| InjecAgent (2024) | Benchmark tool-agent IPI | Evaluation harness | Task trajectories | Tool/data scenarios | No defense | Larger attack corpus |
| AgentDojo (2024) | Security and utility benchmark | Dynamic tool environment | Yes | Environment state | Supports evaluated defenses | Realistic benchmark suites |
| CaMeL (2025) | Prevent untrusted data from changing control flow | Protective system layer | Program execution | Explicit control/data flows and capabilities | Yes | Stronger formal design and provable-security scope |
| RTBAS (2025) | Integrity and confidentiality for tool agents | Before tool execution | Yes | Information-flow dependencies | Yes, with selective confirmation | IFC-based dependency screening |
| MELON (2025) | Detect IPI through masked re-execution | Before tool action | Re-executes trajectory | Causal dependence on user task | Prevents detected action | Model counterfactual comparison |
| AgentArmor (2025) | Program analysis over runtime traces | Runtime trace monitor | Yes | CFG, DFG, PDG and property registry | Yes | Closest overlap; richer program representation |
| Adaptive Attacks (2025) | Test defenses under adaptive attack | Evaluation | Yes | Attack-dependent | No | Shows non-adaptive evaluation is insufficient |
| AgentSentry (2026) | Diagnose temporal causal takeover and continue safely | Tool-return boundaries | Yes | Counterfactual causal localization | Mitigates and continues | Context purification after diagnosis |
| AttriGuard (2026) | Attribute proposed tool calls to user intent or untrusted observations | Before tool execution | Yes | Action-level causal attribution | Yes | Parallel counterfactual model runs |
| Agent Flight Recorder | Enforce trusted metadata, executed history, and artifact links | Before executor invocation | Yes, successful actions only | Session-local named artifact graph | Yes | Explicit execution-state semantics and compact reproducible artifact |

## Closest prior work

### AgentArmor

AgentArmor is the closest conceptual neighbor. It treats runtime traces as programs, reconstructs control and data dependencies, attaches security properties, and enforces policies with a type system. Agent Flight Recorder uses a much smaller state model and does not reconstruct a PDG. The manuscript must cite AgentArmor prominently and avoid claiming first use of runtime traces, data-flow graphs, or policy enforcement for agent security.

A credible comparison should test both systems on common AgentDojo-style tasks or implement a documented approximation of AgentArmor's session/data-flow policy. Comparing only against a deliberately weak point-action baseline is insufficient.

### CaMeL

CaMeL separates trusted control flow from untrusted data and uses capabilities to prevent unauthorized exfiltration. Its security objective overlaps the restricted-artifact upload rule. Agent Flight Recorder differs by observing proposals from an existing agent rather than generating a trusted program from the user query. That difference trades stronger guarantees for easier integration, but the current artifact has not measured the tradeoff.

### RTBAS

RTBAS applies information-flow control and asks for user confirmation only when integrity or confidentiality cannot be established. This overlaps both lineage propagation and Review decisions. Agent Flight Recorder's action-specific approval and executed-only history are implementation details worth measuring, not grounds for a broad originality claim.

### AgentSentry and AttriGuard

These systems diagnose whether untrusted observations caused a tool action through counterfactual model executions. Agent Flight Recorder does not infer causality. It relies on trusted adapter labels and declared artifact links. This makes decisions cheap and deterministic but shifts correctness to the adapter.

## Benchmark implications

The current ten-trace corpus is a correctness suite, not a competitive security benchmark. The next evaluation must include:

- AgentDojo or InjecAgent tasks adapted to the supported tool catalog;
- adaptive attack variants rather than one fixed "ADMIN OVERRIDE" string;
- benign tasks with unrelated sensitive and public artifacts;
- missing, stale, cross-session, and adversarially selected artifact references;
- comparison with a program/data-flow baseline stronger than the current session heuristic;
- explicit measurement of adapter labeling errors.

The 90-run Azure study observed no upload proposal. It cannot compare attack prevention because the gate received no live attack action. Keep it as an adapter-stability and model-behavior result.

## Defensible claims

The current evidence supports these claims:

- The implementation records only successfully executed actions as causal history.
- Denied and failed producers do not create usable artifacts.
- Sensitivity propagates through declared, session-local artifact links.
- The fixed synthetic corpus distinguishes unrelated public and restricted exports in one session.
- The gate prevents executor invocation for labeled blocked actions.
- Live Azure proposals, model stops, approvals, and synthetic outputs are recorded without requesting private reasoning.

The evidence does not support these claims:

- first trajectory-aware agent defense;
- first runtime tool-action firewall;
- general resistance to indirect prompt injection;
- superiority to AgentArmor, CaMeL, RTBAS, AgentSentry, or AttriGuard;
- production readiness;
- correctness when trusted adapters assign wrong labels or omit dependencies.

## Primary sources

- Greshake et al. *Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* arXiv:2302.12173. https://arxiv.org/abs/2302.12173
- Zhan et al. *InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents.* ACL Findings 2024. https://arxiv.org/abs/2403.02691
- Debenedetti et al. *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.* NeurIPS Datasets and Benchmarks 2024. https://arxiv.org/abs/2406.13352
- Debenedetti et al. *Defeating Prompt Injections by Design.* arXiv:2503.18813. https://arxiv.org/abs/2503.18813
- Zhong et al. *RTBAS: Defending LLM Agents Against Prompt Injection and Privacy Leakage.* arXiv:2502.08966. https://arxiv.org/abs/2502.08966
- Zhu et al. *MELON: Indirect Prompt Injection Defense via Masked Re-execution and Tool Comparison.* arXiv:2502.05174. https://arxiv.org/abs/2502.05174
- Wang et al. *AgentArmor: Enforcing Program Analysis on Agent Runtime Trace to Defend Against Prompt Injection.* arXiv:2508.01249. https://arxiv.org/abs/2508.01249
- Zhan et al. *Adaptive Attacks Break Defenses Against Indirect Prompt Injection Attacks on LLM Agents.* NAACL Findings 2025. https://aclanthology.org/2025.findings-naacl.395/
- Zhang et al. *AgentSentry: Mitigating Indirect Prompt Injection in LLM Agents via Temporal Causal Diagnostics and Context Purification.* arXiv:2602.22724. https://arxiv.org/abs/2602.22724
- He et al. *AttriGuard: Defeating Indirect Prompt Injection in LLM Agents via Causal Attribution of Tool Invocations.* arXiv:2603.10749. https://arxiv.org/abs/2603.10749
