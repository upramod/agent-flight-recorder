# Related-work comparison and positioning

Reviewed: 2026-09-17

## Position

A broad claim that Agent Flight Recorder is the first trajectory-aware runtime defense is not supportable. Prior work already constrains data and control flow around tool use, analyzes agent traces, re-executes trajectories, or attributes tool calls to trusted and untrusted context.

The paper should make a narrower systems claim. Agent Flight Recorder places a deterministic gate directly before tool execution, uses trusted structured metadata plus successful executed history, propagates artifact sensitivity through declared lineage, and records Review as a distinct enforcement state. Its strongest evidence is now a preregistered 120-pair AgentDojo evaluation rather than the original synthetic traces.

## Comparison matrix

| Work | Main role | Enforcement or analysis point | Trajectory/data-flow mechanism | Evaluation relevance | Distinction from Agent Flight Recorder |
|---|---|---|---|---|---|
| Greshake et al. (2023) | Establish indirect prompt injection | Attack study | Shows untrusted retrieved data can steer downstream actions | Threat motivation | No runtime defense |
| InjecAgent (2024) | Benchmark indirect prompt injection in tool agents | Evaluation harness | Tool-integrated attack tasks | Benchmark precedent | Larger heterogeneous attack corpus |
| AgentDojo (2024) | Dynamic benchmark for attacks and defenses | Tool-agent environment | Stateful tasks and security evaluators | Primary benchmark used here | Evaluation environment, not this policy design |
| Agent Security Bench (2025) | Broad agent-security benchmark | Multi-scenario evaluation | Attacks and defenses across prompts, tools, and memory | Security-utility evaluation precedent | Broader attack surface and model set |
| CaMeL (2025) | Control/data-flow defense | Protective system layer | Trusted control flow, explicit data flow, capabilities | Closest design principle | Stronger structural separation; different integration model |
| MELON (2025) | Detect injection-driven actions | Before action execution | Masked re-execution and tool-call comparison | Defense comparison | Uses model counterfactuals rather than trusted metadata/history |
| Adaptive Attacks (2025) | Stress-test prompt-injection defenses | Evaluation | Optimizes attacks against the defense | Claim-boundary requirement | Shows static success does not imply adaptive robustness |
| AgentArmor (2025) | Program analysis over agent traces | Runtime monitor | CFG/DFG/PDG plus property/type analysis | Closest trace-analysis neighbor | Richer program representation; Agent Flight Recorder is smaller and deterministic after metadata assignment |
| Tool firewalls (2025) | Modular tool-input/output defense | Agent-tool interface | Minimization and sanitization around tool calls | Strong benchmark baseline and benchmark critique | Filters tool traffic rather than accumulating executed-history risk |
| AttriGuard (2026) | Causal attribution of tool invocations | Before execution | Parallel counterfactual replay | Strong runtime-defense comparison | Infers causal support through re-execution; Agent Flight Recorder does not infer model causality |
| Automated attack evaluation (2026) | Stronger AgentDojo attacks | Evaluation | Black-box and white-box optimization | Future robustness requirement | Demonstrates attack strength is model- and optimizer-dependent |
| Agent Flight Recorder | Runtime enforcement | Immediately before tool execution | Trusted metadata, successful executed history, declared artifact lineage | 120-pair preregistered AgentDojo evaluation | Explicit execution-state semantics and compact deterministic gate |

## Closest design neighbors

### CaMeL

CaMeL derives trusted control and data flow from the user request and uses capabilities to prevent unauthorized information flow. Agent Flight Recorder instead monitors proposals from an existing agent and accepts security metadata from trusted adapters. That choice makes the mechanism easier to insert at a tool boundary, but it gives weaker guarantees when adapter labels or lineage declarations are wrong. The paper should treat this as a design tradeoff, not a superiority claim.

### AgentArmor

AgentArmor reconstructs runtime behavior as graph-based program representations and applies program-analysis concepts to security checking. This overlaps directly with the idea that agent traces contain security-relevant structure. Agent Flight Recorder uses a smaller state model: successful executed actions plus a session-local artifact graph. Its paper-level contribution is therefore the explicit enforcement semantics and paired evidence, not first use of trace structure.

### MELON and AttriGuard

MELON and AttriGuard both ask whether a proposed tool action depends on malicious or untrusted context by re-running or counterfactually modifying the model context. Agent Flight Recorder does not perform model-based causal inference. Once trusted action metadata is assigned, its decision is deterministic. The cost is dependence on metadata quality; the benefit is that no second model execution is required for the policy decision.

### Tool firewalls

Recent firewall-style defenses act at the agent-tool interface and report strong results across public benchmarks, while also arguing that benchmark weaknesses can make defenses appear stronger than they are. This is directly relevant to the claim boundary here. The v2 result is evidence under one AgentDojo configuration, not proof against stronger adaptive or optimization-based attacks.

## Evaluation position after v2

The evidence hierarchy is now:

1. **Independent v2:** 120 unique selected AgentDojo workspace pairs, 20/120 baseline attacks versus 0/120 with Agent Flight Recorder, exact McNemar p=1.91e-06. Utility fell from 61/120 to 35/120 under `Review=deny`.
2. **First preregistered holdout:** 30 pairs, 2/30 versus 0/30 attacks, directionally consistent but underpowered.
3. **Repeated known-pair study:** five repetitions of the same 30 identities. Useful for stochastic behavior, not independent confirmatory sample size.
4. **Post-hoc Review sensitivity:** evidence that review handling drives much of the utility penalty. It cannot replace the confirmatory `Review=deny` result.
5. **Synthetic engineering tests:** useful for state semantics, lineage, failure handling, and metadata corruption. They are not the primary security benchmark.

## Claims the paper can make

- Under the frozen AgentDojo v2 conditions, Agent Flight Recorder reduced observed attack success from 20/120 to 0/120 in paired evaluation.
- The paired security difference was statistically strong under the declared exact McNemar test.
- The strict `Review=deny` configuration imposed a substantial utility cost, 61/120 to 35/120.
- Successful execution history and tool-boundary enforcement can be implemented without access to private chain-of-thought.
- Post-hoc sensitivity evidence indicates that Review handling is part of the security-utility mechanism and should be measured explicitly.

## Claims to avoid

- universal prevention of prompt injection;
- zero population attack probability;
- superiority to CaMeL, AgentArmor, MELON, AttriGuard, or firewall defenses without direct matched comparison;
- robustness to adaptive attacks;
- production readiness;
- correctness under compromised metadata adapters;
- preservation of baseline utility under the confirmatory policy.

## Primary sources

1. Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., Fritz, M. *Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* AISec 2023 / arXiv:2302.12173.
2. Zhan, Q., Liang, Z., Ying, Z., Kang, D. *InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents.* Findings of ACL 2024. DOI: 10.18653/v1/2024.findings-acl.624.
3. Debenedetti, E., Zhang, J., Balunović, M., Beurer-Kellner, L., Fischer, M., Tramèr, F. *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.* arXiv:2406.13352, 2024.
4. Zhang, H. et al. *Agent Security Bench (ASB): Formalizing and Benchmarking Attacks and Defenses in LLM-based Agents.* ICLR 2025.
5. Debenedetti, E. et al. *Defeating Prompt Injections by Design.* arXiv:2503.18813, 2025.
6. Zhu, K., Yang, X., Wang, J., Guo, W., Wang, W. Y. *MELON: Indirect Prompt Injection Defense via Masked Re-execution and Tool Comparison.* arXiv:2502.05174, 2025.
7. Zhan, Q., Fang, R., Panchal, H. S., Kang, D. *Adaptive Attacks Break Defenses Against Indirect Prompt Injection Attacks on LLM Agents.* Findings of NAACL 2025. DOI: 10.18653/v1/2025.findings-naacl.395.
8. Wang, P. et al. *AgentArmor: Enforcing Program Analysis on Agent Runtime Trace to Defend Against Prompt Injection.* arXiv:2508.01249, 2025.
9. Bhagwatkar, R. et al. *Indirect Prompt Injections: Are Firewalls All You Need, or Stronger Benchmarks?* arXiv:2510.05244, 2025.
10. He, Y., Zhu, H., Li, Y., Shao, S., Yao, H., Liu, Z., Qin, Z. *AttriGuard: Defeating Indirect Prompt Injection in LLM Agents via Causal Attribution of Tool Invocations.* USENIX Security 2026, pp. 1547–1566.
11. Hofer, D., Debenedetti, E., Tramèr, F. *Assessing Automated Prompt Injection Attacks in Agentic Environments.* arXiv:2606.10525, 2026.
