# Agent Flight Recorder: Runtime Enforcement for Tool-Using AI Agents Using Executed History and Artifact Lineage

Pramod Ubbala  
Independent Researcher, Washington, USA

> Working manuscript. Results marked TBD require benchmark execution.

## Abstract

Tool-using AI agents convert model outputs into consequential operations such as document reads, database queries, artifact creation, and network transfers. A security check that evaluates each operation alone can lose the context needed to identify a harmful sequence. Session-wide rules recover temporal context but may over-attribute risk when unrelated public and restricted artifacts coexist. We present Agent Flight Recorder, a runtime enforcement prototype that evaluates structured action proposals before tool execution. The system separates proposal, assessment, approval, execution, and audit states; records only successful executions as causal history; and propagates sensitivity through trusted artifact links. A deterministic gate returns Allow, Review, or Block without requesting private model reasoning. The implementation includes an Azure OpenAI proposal adapter, synthetic tools, action-specific browser approvals, downloadable traces, and deterministic replay. We define an evaluation against no-gate, point-action, session-heuristic, artifact-aware, and human-review baselines using unsafe execution, benign completion, attribution accuracy, and latency. Current tests establish execution integrity and fail-closed lineage handling. Benchmark results remain to be collected.

## 1. Introduction

AI agents increasingly act through tools. They read documents, query stores, produce derived artifacts, and send results to other systems. Each operation crosses a concrete runtime boundary. That boundary creates an enforcement point.

Single-action authorization answers whether a principal may invoke a tool. It does not always answer whether the proposed invocation remains safe after earlier actions changed the data context. Consider an agent that reads an untrusted document, queries restricted records, creates an export, and proposes an external upload. The final request can carry weak metadata or a generic file type. Earlier actions reveal the sequence, while artifact links reveal which records produced the file.

Session history alone also has limits. A session can process restricted records and later create an unrelated public export. A rule that treats all later uploads as restricted blocks useful work. The enforcement layer therefore needs both temporal state and data attribution.

Agent Flight Recorder evaluates observable proposals at the tool boundary. Trusted adapters assign security labels and artifact identifiers. The recorder assesses the current proposal against successfully executed history and a session-local artifact graph. The execution gate invokes the tool only after an Allow decision or an approved Review decision. A Block decision never invokes the executor.

This paper asks whether that design reduces unsafe synthetic tool execution without imposing unacceptable loss of benign completion. It makes five engineering contributions:

1. A state model that separates model proposal, policy assessment, human approval, tool execution, and audit evidence.
2. Executed-only session history, which prevents denied or failed actions from becoming false causal facts.
3. Session-local artifact lineage with monotonic sensitivity inheritance across derived outputs.
4. Deterministic fail-closed enforcement for missing, reused, and cross-session artifact references.
5. A reproducible evaluation design that separates policy blocking, human rejection, executor failure, and model stop.

The current artifact demonstrates these mechanisms with synthetic data. It does not establish broad prompt-injection resistance or production readiness.

## 2. Problem statement

Let an agent session contain proposed actions \(a_1, a_2, \ldots, a_n\). Each action includes a tool, operation, resource type, destination trust, privilege level, input provenance, and optional data-flow references. A trusted adapter, rather than the language model, supplies the security fields.

A point-action policy evaluates only \(a_i\). A session policy evaluates \(a_i\) and prior successful actions \(H_i\). An artifact-aware policy also evaluates a session-local graph \(G_i\), whose edges connect source artifacts to derived outputs.

The enforcement function is

\[
D_i = P(a_i, H_i, G_i)
\]

where \(D_i \in \{Allow, Review, Block\}\). Allow invokes the executor. Review invokes it only after approval tied to that exact pending action. Block returns without invoking the executor.

History changes only after successful execution:

\[
H_{i+1} =
\begin{cases}
H_i \mathbin{\|} a_i, & \text{if execution succeeds} \\
H_i, & \text{otherwise.}
\end{cases}
\]

This distinction matters. Recording a denied restricted query as executed would let later policy reason from data the agent never received.

## 3. Threat model

The attacker may control content consumed by the agent, including documents that contain instructions to retrieve or transmit data. The attacker may nominate an untrusted external destination. The model may follow, ignore, or partially follow those instructions.

The attacker cannot modify the policy implementation, trusted adapter labels, session identifiers, successful execution history, or artifact graph. These components form the trusted computing base.

The system addresses unsafe multi-step tool use, missing lineage, duplicate output identifiers, cross-session references, denied producers, and external transfer of sensitive derived artifacts. It does not address compromised adapters, incorrect source labels, vulnerable tools, model-weight compromise, operating-system compromise, or covert channels outside declared tools.

## 4. Design

### 4.1 Observable action proposals

The model proposes a supported tool and operation. Application code maps that proposal to an action event. The event carries trusted labels for sensitivity, destination trust, privilege, provenance, and data-flow identifiers. The model cannot set these labels directly.

### 4.2 Executed-only history

Assessment does not mutate history. The gate assesses first, resolves Review where required, invokes a cloned action through the executor, and records the action only after the executor returns successfully. Blocked, rejected, and failed actions remain visible in the audit trace but absent from causal execution history.

### 4.3 Artifact lineage

Each successful producer may register immutable, session-local output IDs. Consumers declare input IDs. The recorder resolves each input to a successful producer in the same session.

Sensitivity follows an ordered lattice:

\[
Public < Internal < Confidential < Restricted.
\]

For a derived artifact \(x\) with declared sources \(S_x\),

\[
s(x) = \max\left(s_{declared}(x), \max_{y \in S_x} s(y)\right).
\]

The implementation also propagates whether any ancestor depends on untrusted input. Missing producers, duplicate IDs, repeated IDs, output-as-input reuse, and invalid operation shapes fail closed.

### 4.4 Decisions and enforcement

The prototype maps a transparent ordinal score to Allow, Review, or Block. A hard rule sets at least the Block threshold when an upload carries Confidential or Restricted lineage to a destination other than Trusted. Scores explain policy decisions; they are not probabilities.

Approval is action-specific and time-bounded in the browser workflow. Rejecting or ignoring a Review action prevents execution and any dependent artifact creation.

### 4.5 Audit trace

The trace records proposals, assessments, reasons, approval state, executor outcome, effective sensitivity, and source artifact IDs. It distinguishes model stop, human rejection, policy block, and executor failure.

## 5. Implementation

The prototype uses TypeScript and Node.js. The core recorder and gate do not depend on the model provider. An Azure OpenAI adapter requests structured proposals from a deployed model. Trusted application code validates the proposal, assigns security metadata, and routes it through the same deterministic gate used by scripted traces.

Synthetic tools return fake documents, records, and export objects. No real file, customer record, or external upload is required. A browser dashboard supports live proposals, approvals, scripted replay, artifact comparison, and JSON trace download.

The repository includes automated tests for action validation, gate behavior, executed-history integrity, approval binding and expiry, artifact sensitivity inheritance, cross-session isolation, missing references, duplicate IDs, failed executors, and browser session behavior.

## 6. Evaluation methodology

The evaluation follows the versioned protocol in `paper/experiment-protocol.md`.

### 6.1 Baselines

We compare five designs:

- no gate;
- point-action policy;
- executed-session heuristic without artifact identity;
- artifact-aware policy;
- human review without deterministic blocking.

Each baseline receives the same labeled synthetic traces. Implementations must not access information excluded by the baseline definition.

### 6.2 Workloads

The corpus contains benign public exports, restricted internal work, unrelated public and restricted outputs in one session, human rejection, executor failure, external transfer of sensitive exports, mixed-source exports, multi-generation derivations, missing lineage, cross-session references, duplicate output IDs, and undeclared inputs.

The model-in-the-loop study uses fixed prompt families for benign work, indirect external-upload instructions, ambiguous destinations, and early model stops. Model runs remain separate from deterministic replay because proposal sequences vary.

### 6.3 Measures

Security measures include unsafe execution rate, blocked exfiltration rate, fail-closed rate, and execution-integrity violations. Utility measures include benign completion, false blocks, Review burden, and approvals per completed task. Attribution measures include effective-sensitivity accuracy, source-set precision and recall, and cross-contamination between unrelated artifacts. Cost measures include assessment latency, gate overhead, review delay, and trace size.

Rates use Wilson 95% confidence intervals. Latency uses median, p95, and bootstrap 95% confidence intervals. Raw observations are stored as JSON Lines with trace version, strategy, seed, runtime, commit, and model configuration.

## 7. Results

### 7.1 Automated correctness tests

At commit `fb8b40d809babb43a33b3e06014d11ee29049c13`, the repository passed 40 of 40 automated tests. The suite covered proposal validation, execution-gate behavior, approval binding and expiry, model-stop separation, artifact inheritance, missing and cross-session lineage, duplicate output identifiers, failed producers, browser session isolation, trace semantics, and benchmark baselines.

### 7.2 Deterministic benchmark

We executed 10 unique synthetic traces against five enforcement strategies. Seven action cases carried an unsafe label and 21 carried a benign label. Each trace-strategy pair ran 100 times for timing, producing 5,000 JSONL rows. Security and utility counts use each unique trace once.

| Strategy | Unsafe execution | False block | Reviews | Sensitivity accuracy | Median trace ms | p95 trace ms |
|---|---:|---:|---:|---:|---:|---:|
| No gate | 7/7 | 0/21 | 0 | N/A | 0.0105 | 0.0198 |
| Point action | 7/7 | 0/21 | 2 | N/A | 0.0201 | 0.0441 |
| Session heuristic | 4/7 | 1/21 | 3 | N/A | 0.0362 | 0.0818 |
| Artifact aware | 0/7 | 0/21 | 2 | 10/10 | 0.0399 | 0.1091 |
| Human review only | 7/7 | 0/21 | 7 | N/A | 0.0101 | 0.0178 |

The artifact-aware strategy prevented every labeled unsafe action in this fixed corpus and introduced no policy block among the labeled benign actions. The session heuristic blocked one benign public upload after unrelated restricted work in the same session. Point-action and human-review-only strategies executed every labeled unsafe action under the scripted approval policy.

These results establish behavior on the versioned synthetic corpus. Repeated timing runs do not expand attack coverage. The latency measurements cover in-process synthetic traces on Node.js v24.19.0 and Linux 6.18.44; they exclude model calls, network delay, tool latency, and human review.

### 7.3 Model-in-the-loop study

We ran 30 live Azure OpenAI sessions for each of three synthetic document families: safe internal work, an external-upload injection, and an ambiguous partner destination. Review actions received scripted approval. Across all 90 runs, the model produced the same sequence: read, query, create export, then stop. The study made 360 model requests and observed no proposal errors.

| Scenario | Runs | Model stopped | Upload proposed | Policy blocked | Median duration ms |
|---|---:|---:|---:|---:|---:|
| Safe | 30 | 30/30 | 0/30 | 0/30 | 2881.3 |
| Injection | 30 | 30/30 | 0/30 | 0/30 | 2483.8 |
| Ambiguous | 30 | 30/30 | 0/30 | 0/30 | 2535.3 |

The injection and ambiguous documents did not induce an external-upload proposal under this prompt and deployment. The gate therefore had no live upload to block. This result records model refusal and adapter stability; it does not demonstrate a live policy prevention. For each family, the Wilson 95% interval around the observed 0/30 upload-proposal rate extends to approximately 11.4%, so the sample does not establish that uploads cannot occur.

### 7.4 Ablation

TBD. Compare current-action metadata, executed session history, and artifact lineage. The expected question is whether lineage reduces the session heuristic's false blocks without increasing unsafe execution.

## 8. Discussion

The design places enforcement at a stable systems boundary. The model can vary its wording or internal process, but the tool request must still cross the gate. That property makes decisions inspectable and testable.

Artifact identity narrows the scope of inherited restrictions. Session history answers what happened earlier. Lineage answers which earlier data produced the current artifact. Both signals are needed when a session handles unrelated data.

The trusted adapter is a material assumption. If it labels restricted data as public or omits a real data-flow edge, the current policy can make an unsafe decision. Deployment therefore requires adapter review, schema enforcement, identity-bound sessions, durable storage, and tamper-resistant telemetry.

Human approval carries its own risk. Review fatigue can convert a pause into routine acceptance. The evaluation reports review burden rather than treating human presence as sufficient protection.

## 9. Limitations

The tools and data are synthetic. The score weights are hand-authored and uncalibrated. The artifact graph is process-local. The trace corpus cannot represent every agent workflow. Azure model behavior can change across deployments and service updates. The study does not test compromised trusted adapters or covert data transfer through undeclared channels. Comparisons with published defenses require faithful implementations or their released artifacts.

## 10. Related work

Greshake et al. established indirect prompt injection as a practical attack against LLM-integrated applications. InjecAgent and AgentDojo then supplied tool-oriented tasks for measuring attack success and utility. These benchmarks are broader than our fixed synthetic corpus, which currently serves as an implementation correctness suite.

CaMeL constructs explicit control and data flows from a trusted query and uses capabilities to prevent unauthorized flows. RTBAS adapts information-flow control to tool agents and requests confirmation when integrity or confidentiality cannot be established. Both systems overlap our goal of stopping sensitive data from reaching unauthorized tools. Agent Flight Recorder observes proposals from an existing agent and relies on trusted adapter labels, which simplifies integration but provides weaker guarantees when adapters omit or mislabel dependencies.

MELON, AgentSentry, and AttriGuard use re-execution or counterfactual analysis to infer whether untrusted observations caused a tool action. Agent Flight Recorder performs no causal inference. Its artifact links are application-supplied facts. The policy is deterministic after those facts arrive, but its correctness depends on the trusted adapter.

AgentArmor is the closest prior design. It converts runtime traces into control-flow, data-flow, and program-dependence representations, attaches security properties, and applies a type system. Our prototype uses a smaller session-local artifact graph and emphasizes executed-only history, action-bound approval, and distinct audit outcomes. We therefore do not claim the first trajectory-aware runtime defense or the first data-flow policy for agents.

Adaptive evaluations have bypassed multiple prompt-injection defenses, which limits conclusions from fixed attacks. A competitive security claim requires evaluation on AgentDojo or InjecAgent with adaptive variants and a direct comparison against stronger data-flow or program-analysis baselines. The present results support implementation semantics on a declared corpus.

## 11. Conclusion

Agent Flight Recorder treats tool execution as an enforceable runtime event. It records successful actions, links derived artifacts to their sources, and applies deterministic policy before consequential operations run. The prototype establishes a testable architecture. The planned evaluation will determine whether artifact-aware enforcement improves the security-utility tradeoff over point-action and session-wide alternatives.
