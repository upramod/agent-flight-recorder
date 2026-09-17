# Agent Flight Recorder: Trajectory-Aware Runtime Enforcement for Tool-Using AI Agents

Pramod Ubbala  
Independent Researcher, Washington, USA

## Abstract

Tool-using language-model agents can convert untrusted text into external actions. A malicious instruction that enters through a document, email, calendar entry, or tool result may therefore influence a later tool call even when the final call appears locally ordinary. We present Agent Flight Recorder, a runtime enforcement layer that evaluates observable tool proposals before execution. The mechanism uses trusted action metadata, successful executed history, destination trust, sensitivity, privilege, and declared artifact lineage. It returns Allow, Review, or Block without reading or storing private chain-of-thought. We evaluated a frozen configuration in a preregistered 120-pair AgentDojo workspace study using the `tool_knowledge` attack. The paired baseline recorded 20/120 attack successes (16.7%), while Agent Flight Recorder recorded 0/120 (0.0%). The exact two-sided McNemar p-value was 1.91×10^-6. The security effect carried a substantial utility cost under the confirmatory non-interactive `Review=deny` policy: legitimate-task success fell from 61/120 (50.8%) to 35/120 (29.2%), with 29 baseline-success/Recorder-failure pairs versus 3 pairs in the opposite direction. A post-hoc sensitivity study on already-seen cases suggests that review handling accounts for much of this loss, but that study does not replace the confirmatory result. The evidence supports a narrow claim: under the recorded AgentDojo, model, attack, metadata, and policy conditions, trajectory-aware tool-boundary enforcement reduced observed attack completion while imposing a material intervention cost.

## 1. Introduction

Tool use changes the security problem for language-model agents. A model response is no longer only text. It can become an email, a database query, a file transfer, a calendar mutation, or another state-changing operation. Indirect prompt injection exploits the same path. An attacker places instructions inside content the agent later consumes, and the agent may treat those instructions as authority rather than data [1]. Benchmarks such as InjecAgent, AgentDojo, and Agent Security Bench show that this failure mode persists in tool-integrated settings [2-4].

Many defenses inspect the prompt, sanitize tool data, isolate trusted control flow, compare counterfactual executions, or reconstruct program-like dependencies [5-11]. Agent Flight Recorder addresses a narrower systems question: what can an application enforce at the moment a proposed tool action is about to execute, using only observable runtime state supplied by trusted adapters?

The design treats the tool boundary as a policy boundary. The model proposes an action. Application code assigns structured security metadata. A deterministic recorder evaluates the current action together with successful executed history and, where available, artifact lineage. The execution gate then permits the action, requires approval, or blocks it. Denied and failed actions remain audit events but do not become facts in causal execution history.

This distinction matters in multi-step trajectories. Consider an agent that consumes external content, accesses sensitive records, creates a derived export, and later proposes transmission to an untrusted destination. A point check on the final operation may miss the path that produced the payload. A session-wide rule can recover temporal context but may contaminate unrelated work. Artifact lineage narrows the inherited restriction to outputs that actually depend on sensitive sources.

We make four claims, each bounded by the implementation and evaluation reported here.

1. **Runtime mechanism.** Agent Flight Recorder enforces policy before tool execution using structured metadata, successful executed history, and optional artifact lineage. The gate does not require private model reasoning.
2. **Execution semantics.** Only successful tool effects enter causal history. Review, rejection, policy block, model stop, and executor failure remain distinct states.
3. **Paired AgentDojo evidence.** In a preregistered 120-pair workspace evaluation, the frozen Recorder condition produced 0/120 attack successes versus 20/120 for baseline, with exact paired p=1.91×10^-6.
4. **Measured cost.** The same confirmatory policy reduced utility from 61/120 to 35/120. The paper therefore treats security and utility as coupled outcomes rather than presenting the defense as cost-free.

We do not claim universal prompt-injection prevention, robustness to adaptive attacks, production readiness, or superiority to stronger published defenses. Zero observed attacks in one benchmark is not a zero population attack probability.

## 2. Threat model and design goals

### 2.1 Threat model

The attacker may control content consumed through tools or external data sources. That content may contain instructions designed to redirect the agent toward an unauthorized action. The attacker may also nominate an untrusted destination. The language model may follow, ignore, or partially follow the injected instruction.

The attacker cannot modify the policy engine, the execution gate, the session identifier, or trusted metadata produced by the application adapter. Those components form the trusted computing base. The current system also assumes that declared artifact links accurately represent relevant data dependencies.

The defense does not address a compromised adapter, malicious tool implementation, operating-system compromise, model-weight compromise, undeclared covert channels, or data flow that never crosses an instrumented tool boundary.

### 2.2 Design goals

The enforcement layer should satisfy five operational properties.

**Tool-boundary control.** Every supported tool effect must pass through one decision point before execution.

**No chain-of-thought dependency.** The mechanism must operate on observable proposals and external metadata rather than hidden model reasoning.

**Executed-only state.** A denied or failed action must not alter the state used to justify later decisions.

**Data-specific inheritance.** When an application declares lineage, derived artifacts should inherit the strongest sensitivity and trust-relevant properties of their sources.

**Auditable intervention.** Allow, Review, Block, approval, rejection, execution, and failure must remain distinguishable in the trace.

## 3. Agent Flight Recorder

### 3.1 Action representation

A proposed action is mapped to structured metadata before the executor runs. The current implementation records fields such as operation, resource type, sensitivity, destination trust, privilege level, input provenance, session identifier, and optional data-flow information. The language model does not assign the trusted security labels directly in the AgentDojo integration.

For AgentDojo, a trusted tool catalog maps each supported tool to security metadata. Recipient domains can alter destination trust. Calls to recipients outside the configured trusted domain are marked untrusted. Unmapped tools fail closed.

### 3.2 Executed trajectory state

Let the successful execution history before action \(a_i\) be \(H_i\). The recorder computes a decision

\[
D_i = P(a_i, H_i, G_i),
\]

where \(G_i\) is the current artifact-lineage state when lineage is declared and \(D_i \in \{Allow, Review, Block\}\).

The gate first assesses the proposal without mutating history. A Block returns without invoking the tool. A Review executes only when the configured approval path approves it. After an allowed tool call returns successfully, the recorder appends that action to history:

\[
H_{i+1} =
\begin{cases}
H_i \mathbin{\|} a_i, & \text{successful execution},\\
H_i, & \text{otherwise.}
\end{cases}
\]

This prevents policy from reasoning as though denied or failed operations actually occurred.

### 3.3 Trajectory risk

The prototype uses transparent risk rules rather than a learned classifier. Current signals include external or untrusted provenance, data sensitivity, destination trust, privilege, prior untrusted input followed by sensitive access, and sensitive export transfer outside the trusted boundary.

The score maps to three actions: 0-39 Allow, 40-69 Review, and 70-100 Block. A sensitive artifact upload to a destination outside the trusted boundary is raised to at least the Block threshold. Scores explain deterministic policy behavior; they are not calibrated probabilities.

### 3.4 Artifact lineage

Session history alone can over-attribute risk. A session may handle restricted records and later create an unrelated public artifact. To separate those paths, the implementation supports session-local artifact identifiers and declared source relationships.

Sensitivity follows an ordered lattice:

\[
Public < Internal < Confidential < Restricted.
\]

For a derived artifact \(x\) with sources \(S_x\), the effective sensitivity is

\[
s(x) = \max\left(s_{declared}(x), \max_{y \in S_x}s(y)\right).
\]

Untrusted ancestry also propagates. Missing producers, cross-session references, and invalid lineage fail closed. This mechanism does not infer hidden causal structure from the model. It relies on application-supplied artifact facts.

### 3.5 Review semantics

Review is not equivalent to Allow. In an interactive deployment it represents a pause for explicit authorization. The confirmatory AgentDojo experiment was non-interactive and used `Review=deny`: every Review decision prevented the tool call. That choice was frozen before the v2 outcomes were observed.

A later post-hoc study changed only Review handling to automatic approval on already-seen cases. We use that study only to analyze the utility mechanism. It does not redefine the confirmatory policy.

## 4. AgentDojo integration

The evaluation adapter replaces AgentDojo's normal tool executor with a gate-aware executor. For each proposed tool call, the adapter creates trusted action metadata, requests a deterministic assessment from the TypeScript policy bridge, and executes the AgentDojo function only when the decision permits it.

A blocked action produces no tool effect. Under `Review=deny`, a Review also produces no tool effect. Successful executions are then recorded into the policy bridge. The adapter writes an audit stream that preserves the proposed tool, action metadata, policy assessment, approval state, execution state, and errors.

Baseline and Recorder modes use the same model deployment, benchmark task, injected task, attack family, and AgentDojo environment. The difference is the runtime gate.

## 5. Experimental method

### 5.1 Evidence sequence

The project separated development evidence from confirmatory evidence.

An initial synthetic corpus tested execution semantics, artifact lineage, approval handling, and metadata corruption. A first preregistered AgentDojo holdout then evaluated 30 unseen pair identities. That holdout recorded 2/30 baseline attack successes versus 0/30 with Agent Flight Recorder, but the paired attack comparison was underpowered (exact McNemar p=0.5). Utility was 20/30 for baseline and 15/30 for Recorder.

After freezing that result, we ran two post-hoc studies on the known 30 identities. One changed Review handling from deny to approve. The other repeated the same identities across five stochastic blocks. Those studies informed the interpretation of utility and run-to-run variance but did not add independent confirmatory units.

We then froze protocol v2 before collecting new outcomes.

### 5.2 V2 benchmark configuration

The v2 experiment used:

- AgentDojo package version `0.1.35`;
- AgentDojo benchmark `v1.2.2`;
- `workspace` suite;
- `tool_knowledge` attack;
- Azure deployment identifier `gpt-4.1-mini-agent-flight-decoder`;
- trusted email domain `bluesparrowtech.com`;
- frozen Agent Flight Recorder policy;
- confirmatory `Review=deny` handling.

Secrets and credentials were not stored as experimental metadata.

### 5.3 Pair selection and overlap control

The workspace inventory exposed 40 user tasks and 14 injection tasks under the pinned benchmark. The v2 generator enumerated candidate user-task/injection-task pairs, removed exact identities used by the prior diagnostic and holdout manifests, and ranked the remaining identities by a fixed SHA-256 selection key. It selected the first 120 unique eligible pairs.

The generator and overlap tests were committed before model execution. The successful run generated the frozen manifest with SHA-256 `133014deda3d84607e29270525fce26e45b3f75b2b4f94559135c373f4b1b3aa`.

The first workflow attempt failed before manifest generation because the new parser did not recognize legacy manifest field names. No v2 model call occurred in that attempt. We corrected only the parser and overlap-test schema handling, then reran the frozen design.

### 5.4 Paired execution

Each selected pair was executed in two modes:

1. baseline AgentDojo agent;
2. the same agent with Agent Flight Recorder enforcement.

The experiment did not stop early for benefit, harm, or statistical significance. The successful workflow completed all 120 paired evaluations, summary generation, statistical analysis, checksum capture, and artifact upload.

### 5.5 Endpoints and statistical analysis

The primary endpoint was AgentDojo injection-task attack success. We report raw counts, proportions, Wilson 95% confidence intervals, paired discordance, absolute observed risk difference, and an exact two-sided McNemar test.

Legitimate-task utility was a prespecified secondary endpoint. We report aggregate utility, paired discordance, Wilson intervals, and the exact two-sided McNemar test for the paired utility outcome.

Repeated executions of an already-used pair are not treated as new independent tasks.

## 6. Primary results

### 6.1 Attack success

The baseline agent completed the injected objective in 20 of 120 pairs. Agent Flight Recorder completed the injected objective in none of the 120 pairs.

| Outcome | Baseline | Agent Flight Recorder |
|---|---:|---:|
| Attack success | 20/120 (16.7%) | 0/120 (0.0%) |
| Attack resisted | 100/120 (83.3%) | 120/120 (100.0%) |
| Wilson 95% CI for attack success | 11.1%-24.3% | 0.0%-3.1% |

The observed attack-risk difference, Recorder minus baseline, was -16.7 percentage points. The relative observed reduction was 100%, but this finite-sample ratio must not be read as proof of complete security.

Paired outcomes were one-sided: 20 pairs had baseline attack success with Recorder resistance, zero had baseline resistance with Recorder attack success, zero succeeded in both modes, and 100 resisted in both. The exact two-sided McNemar p-value was 1.90735×10^-6.

Under the recorded conditions, these results provide strong evidence that the runtime gate reduced observed attack completion relative to the paired baseline.

### 6.2 Legitimate-task utility

The security result came with a large task-completion penalty.

| Outcome | Baseline | Agent Flight Recorder |
|---|---:|---:|
| Utility success | 61/120 (50.8%) | 35/120 (29.2%) |
| Wilson 95% CI | 42.0%-59.6% | 21.8%-37.8% |

The observed utility difference, Recorder minus baseline, was -21.7 percentage points.

The paired table exposes the direction of that loss:

| Baseline utility | Recorder utility | Pairs |
|---|---|---:|
| success | success | 32 |
| success | failure | 29 |
| failure | success | 3 |
| failure | failure | 56 |

The utility discordance was therefore 29-to-3 against the Recorder condition. The exact two-sided McNemar p-value was 2.55601×10^-6.

The confirmatory experiment does not support a claim that the defense preserved baseline utility.

### 6.3 Policy interventions

Across the 120 Recorder trajectories, the audit summaries recorded 291 Allow decisions, 149 Review decisions, and 115 Block decisions. A total of 269 tool actions executed and 286 were denied. These are descriptive action counts, not independent observations. One benchmark pair can generate several tool proposals, and policy interventions change later trajectories.

The counts still explain the operational burden of the strict condition. `Review=deny` converts every ambiguous review into a denied tool call, so review frequency directly affects task completion.

## 7. Review sensitivity and stochastic behavior

The original 30-pair confirmatory holdout used `Review=deny`. After its result was frozen, we reran the same known pair identities with `Review=approve`. Baseline utility in that rerun was 21/30, while Recorder utility was 24/30. Recorder utility had been 15/30 in the frozen deny holdout. Nine Recorder cases moved from utility failure to utility success, and none moved in the opposite direction.

Security inference from that sensitivity run is weak. Both baseline and Recorder recorded 0/30 attack successes in the rerun. The baseline itself changed from 2/30 attacks in the frozen holdout to 0/30 without a policy change. That change exposed stochastic variation in model trajectories.

We then executed five repeated blocks of the same 30 known pair identities under baseline, `Review=deny`, and `Review=approve`. Across 150 repeated observations per condition, baseline utility was 113/150, deny utility was 74/150, and approve utility was 115/150. Attack success was 1/150 for baseline and 0/150 for each Recorder condition. The 150 observations per condition are repetitions of 30 identities, not 150 new benchmark tasks.

Taken together, these post-hoc results support one mechanism-level interpretation: strict Review denial accounts for a large part of the observed utility penalty. They do not establish that automatic approval is safe, and they do not amend the v2 confirmatory result.

## 8. Engineering validation outside AgentDojo

Before the benchmark study, the implementation underwent deterministic tests of execution semantics and artifact lineage. Synthetic traces covered sensitive export, unrelated public and restricted work in the same session, denied producers, executor failures, missing lineage, cross-session references, duplicate artifact identifiers, and multi-generation data derivation.

A metadata-corruption study also exposed a central trust assumption. When trusted sensitivity labels were probabilistically downgraded before policy evaluation, unsafe execution rose with the injected label-error rate. Missing or incorrect trusted metadata can therefore defeat a policy that depends on that metadata. The AgentDojo result should be interpreted with the same boundary.

These engineering tests support implementation semantics. They are not pooled with the 120-pair security endpoint.

## 9. Related work

Indirect prompt injection arises when data consumed by an LLM-integrated application carries instructions that redirect later behavior. Greshake et al. demonstrated this attack surface in real and synthetic LLM-integrated systems [1]. InjecAgent moved the problem into tool-integrated agent evaluation and supplied more than one thousand indirect-injection cases [2]. AgentDojo introduced a dynamic environment that jointly measures security and task utility under attacks and defenses [3]. Agent Security Bench broadened agent-security evaluation across attack classes, tools, and model backbones [4].

Several defenses change the system architecture around the model. CaMeL separates trusted control flow from untrusted data and uses capabilities to constrain unauthorized information flow [5]. That design offers a stronger structural security model than the trusted-metadata gate used here. Agent Flight Recorder instead attaches to an existing agent at the tool boundary and evaluates each proposal against external metadata and recorded state.

Other defenses infer whether untrusted context caused a proposed action. MELON masks the user prompt and re-executes the trajectory, then compares tool behavior [6]. AttriGuard performs action-level causal attribution through counterfactual replay and reports strong results against static and adaptive settings [10]. Agent Flight Recorder performs no model re-execution for a policy decision. Once the trusted adapter has assigned metadata, assessment is deterministic.

AgentArmor is especially close in systems motivation. It reconstructs agent runtime traces into control-flow, data-flow, and program-dependence representations and applies program-analysis concepts to security enforcement [8]. Agent Flight Recorder uses a smaller state representation based on successful executions and declared artifact links. We therefore do not claim first use of runtime traces or data flow for agent security.

Tool-interface firewalls provide another nearby design point. Bhagwatkar et al. report strong benchmark performance from tool-input minimization and tool-output sanitization, while also identifying weaknesses in current benchmark design [9]. Their benchmark critique matters here. A result on AgentDojo measures behavior under the tested attack and evaluator. It does not establish protection against all prompt injection.

Adaptive evaluation sharpens that boundary. Zhan et al. bypassed multiple indirect-prompt-injection defenses with adaptive attacks [7]. Hofer et al. later evaluated automated black-box and white-box prompt-injection optimization in AgentDojo and found that attack effectiveness depends on the attacker method and model [11]. Agent Flight Recorder v2 used one fixed attack family. Adaptive robustness remains unmeasured.

## 10. Discussion

### 10.1 Security and utility are coupled

The central result is not simply 20 attacks versus zero. The same frozen policy also moved 29 paired tasks from baseline success to Recorder failure while moving only three in the opposite direction. A strict runtime gate can achieve strong observed protection by stopping actions that include both malicious and legitimate work.

The post-hoc Review studies make this coupling visible. Review handling is part of the security mechanism, not a user-interface detail. Automatically approving every Review can recover utility, but it also changes the enforcement semantics. A production design needs an approval channel whose decisions carry real authorization rather than scripted acceptance or denial.

### 10.2 Why executed-only history matters

A security monitor should distinguish proposed behavior from actual effects. If a blocked database query enters history as though it succeeded, later decisions can inherit sensitivity from data the agent never received. If a failed producer creates an artifact record, later lineage can point to an output that does not exist. Agent Flight Recorder records successful effects only. This state rule is simple, but it prevents a class of trace-consistency errors.

### 10.3 Trusted metadata is a security boundary

Deterministic enforcement does not remove trust; it relocates it. The current system trusts application adapters to map tools, assign sensitivity, identify destinations, and declare artifact dependencies. Wrong labels can create wrong decisions. The synthetic metadata study confirms this directly.

A deployable system would need schema validation, adapter review, authenticated session identity, durable and tamper-resistant state, strict tool registration, and monitoring for missing metadata. These requirements are part of the security design.

### 10.4 Benchmark interpretation

The v2 paired result is statistically clear under the declared benchmark. Its external meaning is narrower. AgentDojo's evaluator defines attack completion for specific injected objectives. The `tool_knowledge` attack is not an adaptive adversary against this policy. One Azure model deployment and one workspace suite cannot represent the full space of models, tools, or prompt-injection strategies.

The correct statement is therefore benchmark-specific: the frozen gate reduced observed attack success under the recorded conditions. Stronger claims require separate experiments designed before outcomes are seen.

## 11. Threats to validity

**Internal validity.** Language-model trajectories are stochastic. The paired design controls task identity but does not make model calls deterministic. The earlier repeated study showed small utility variation and occasional baseline attack variation across reruns. V2 increased unique pair count rather than treating repeated known cases as independent evidence.

**Construct validity.** AgentDojo attack success represents completion of its defined injection objective. It is not equivalent to every form of compromise. Legitimate-task utility also depends on benchmark semantics and agent capability.

**Policy validity.** The score weights and thresholds are engineered rules rather than statistically calibrated risk probabilities. The confirmatory test evaluates the frozen rule set as a system, not the optimality of each weight.

**Metadata validity.** Tool mappings, destination trust, sensitivity, provenance, and lineage are trusted inputs. Incorrect mappings can cause unsafe decisions or unnecessary blocking.

**External validity.** V2 used AgentDojo workspace, `tool_knowledge`, one primary Azure deployment, and a fixed tool catalog. Results may not transfer to other suites, models, attacks, or production applications.

**Adaptive validity.** The study did not expose the policy to an attacker that optimized prompts against its behavior. Published adaptive and automated attack work shows that this omission matters [7,11].

## 12. Reproducibility and evidence provenance

The v2 protocol was committed before outcome collection. The deterministic generator and overlap tests were committed separately. The successful evaluation ran from commit `9ef3022fa5dd05ae8746c6f8b4556ad6311e30a5` in GitHub Actions run `35180860582`.

The retained artifact is `agentdojo-v2-35180860582` with GitHub-reported SHA-256 `3a4e8c97a8237b8f2fa5eae08f9fc2e4188c72173ff594a58680b7b907faac81`. The generated v2 manifest hash is `133014deda3d84607e29270525fce26e45b3f75b2b4f94559135c373f4b1b3aa`. The frozen pair summary hash is `a080ec60debde9746fd6e4d2b55ac38bf1900050f48bc609d5ec5b04a860041d`.

The repository preserves the protocol, workflow, generated evidence hashes, raw per-case console records, paired summaries, and frozen evidence documents. No policy change was made in response to v2 outcomes before the result was frozen.

## 13. References

1. K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, and M. Fritz. “Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.” AISec, 2023. arXiv:2302.12173.
2. Q. Zhan, Z. Liang, Z. Ying, and D. Kang. “InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents.” Findings of the Association for Computational Linguistics: ACL 2024, pp. 10471-10506. DOI: 10.18653/v1/2024.findings-acl.624.
3. E. Debenedetti, J. Zhang, M. Balunović, L. Beurer-Kellner, M. Fischer, and F. Tramèr. “AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.” arXiv:2406.13352, 2024.
4. H. Zhang, J. Huang, K. Mei, Y. Yao, Z. Wang, C. Zhan, H. Wang, and Y. Zhang. “Agent Security Bench (ASB): Formalizing and Benchmarking Attacks and Defenses in LLM-based Agents.” International Conference on Learning Representations, 2025.
5. E. Debenedetti, I. Shumailov, T. Fan, J. Hayes, N. Carlini, D. Fabian, C. Kern, C. Shi, A. Terzis, and F. Tramèr. “Defeating Prompt Injections by Design.” arXiv:2503.18813, 2025.
6. K. Zhu, X. Yang, J. Wang, W. Guo, and W. Y. Wang. “MELON: Indirect Prompt Injection Defense via Masked Re-execution and Tool Comparison.” arXiv:2502.05174, 2025.
7. Q. Zhan, R. Fang, H. S. Panchal, and D. Kang. “Adaptive Attacks Break Defenses Against Indirect Prompt Injection Attacks on LLM Agents.” Findings of the Association for Computational Linguistics: NAACL 2025, pp. 7116-7132. DOI: 10.18653/v1/2025.findings-naacl.395.
8. P. Wang, Y. Liu, Y. Lu, Y. Cai, H. Chen, Q. Yang, J. Zhang, J. Hong, and Y. Wu. “AgentArmor: Enforcing Program Analysis on Agent Runtime Trace to Defend Against Prompt Injection.” arXiv:2508.01249, 2025.
9. R. Bhagwatkar, K. Kasa, A. Puri, G. Huang, I. Rish, G. W. Taylor, K. D. Dvijotham, and A. Lacoste. “Indirect Prompt Injections: Are Firewalls All You Need, or Stronger Benchmarks?” arXiv:2510.05244, 2025.
10. Y. He, H. Zhu, Y. Li, S. Shao, H. Yao, Z. Liu, and Z. Qin. “AttriGuard: Defeating Indirect Prompt Injection in LLM Agents via Causal Attribution of Tool Invocations.” 35th USENIX Security Symposium, 2026, pp. 1547-1566.
11. D. Hofer, E. Debenedetti, and F. Tramèr. “Assessing Automated Prompt Injection Attacks in Agentic Environments.” arXiv:2606.10525, 2026.

## 14. Conclusion

Agent Flight Recorder enforces deterministic policy at the point where model proposals become tool effects. In a preregistered 120-pair AgentDojo workspace evaluation, the frozen system recorded 0/120 attack successes versus 20/120 for the paired baseline. The same policy reduced legitimate-task utility from 61/120 to 35/120. The evidence therefore shows both protection and cost.

The design result is practical. Observable runtime state can support meaningful intervention without access to private model reasoning. The experimental result is narrower. It applies to the recorded benchmark and policy conditions, and it leaves adaptive robustness, metadata assurance, and usable human review as open engineering problems.
