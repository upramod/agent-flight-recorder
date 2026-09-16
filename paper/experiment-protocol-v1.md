# Agent Flight Recorder Experimental Protocol v1

**Frozen:** 2026-09-16

## Research question

Does trajectory-aware runtime policy enforcement reduce successful prompt-injection attacks compared with an otherwise equivalent unprotected agent while preserving legitimate task completion?

## Primary hypothesis

Under fixed benchmark and model conditions, Agent Flight Recorder will reduce attack success relative to the baseline agent without a material reduction in legitimate-task success.

## Null hypothesis

There is no difference in attack success between baseline and Agent Flight Recorder under the recorded conditions.

## Experimental unit and pairing

A benchmark case is a fixed `(user task, injection task)` pair. Each selected case is evaluated in both modes:

1. baseline agent;
2. the same agent with Agent Flight Recorder enforcement.

The user task, injection task, attack method, model deployment, benchmark version, tool definitions, and run configuration remain fixed within a paired comparison.

## Primary endpoint

**Attack success**, using AgentDojo's injection-task security evaluator. A true injection security result means that the injection objective succeeded. Reporting must therefore use the explicit terms `attack_success` and `attack_resisted`; the ambiguous label `security` must not be used for aggregate interpretation.

## Secondary endpoints

- legitimate-task utility success;
- attack resistance;
- Allow / Review / Block counts;
- denied tool executions;
- policy-decision latency where available;
- false Review and false Block behavior where ground truth permits classification.

## Fixed policy

The policy state frozen after the 30-pair diagnostic evaluation is the starting policy for holdout testing.

Evidence milestone: `v0.2.0-agentdojo-evidence`

Evidence commit: `c4a9a011f14293222e42d143548321b144a40d20`

Policy correction commit: `cd4f36119e5f538e59f6c105dcc7812853e1f8ed`

Regression-test commit: `7f0105f5440665eb277293a5b7e87786c7d79efb`

The diagnostic 30-pair manifest is no longer eligible to guide policy changes before holdout measurement.

## Holdout design

The first confirmatory experiment will use a separately declared holdout set of **30 valid AgentDojo workspace `(user task, injection task)` pairs** that do not duplicate any pair in `integrations/agentdojo/benchmark-manifest.json`.

The holdout manifest must be committed before its benchmark outcomes are inspected. Pair-selection rules and exclusions must be recorded with the manifest.

No policy threshold, scoring rule, provenance rule, trust rule, tool mapping, or regression behavior may be changed after holdout execution begins and before the primary holdout result is frozen.

If the holdout reveals a defect, that result remains the confirmatory result. Any subsequent correction is a new development cycle followed by a new, separately defined evaluation set.

## Initial fixed benchmark conditions

Unless a later protocol amendment is committed before data collection, the first holdout uses:

- AgentDojo: `v1.2.2`;
- suite: `workspace`;
- attack: `tool_knowledge`;
- Flight Recorder review policy: `deny`;
- trusted email domain: `bluesparrowtech.com`;
- same Azure OpenAI deployment configuration used by the frozen 30-pair evidence workflow;
- identical tool catalog and AgentDojo adapter behavior across baseline and Flight Recorder modes.

Secrets and credentials are never committed as experimental metadata.

## Confirmatory analysis

For the 30-pair holdout, report raw paired outcomes before inferential statistics.

Primary comparison:

- baseline attack success versus Flight Recorder attack success.

Report:

- counts and proportions;
- absolute risk difference;
- relative reduction when the baseline rate is non-zero;
- paired discordant counts;
- exact McNemar test for the paired binary attack-success endpoint;
- 95% confidence intervals for observed proportions and, where appropriate, the paired effect estimate.

Secondary utility outcomes must be reported separately. A higher utility count in one finite run must not be described as an improvement without suitable repeated evidence.

With only 30 pairs, inferential results are exploratory/limited by sample size. Effect magnitude and raw outcomes remain central.

## Robustness experiments

Robustness runs occur only after the confirmatory holdout is frozen. They may vary one dimension at a time, including:

- attack family;
- model deployment;
- metadata/provenance error rate;
- destination-trust classification error;
- review behavior.

Each robustness run receives its own manifest/configuration record. Results from different conditions must not be pooled without a declared analysis rule.

## Ablation study

Ablations may remove one policy signal at a time:

- trajectory history;
- input provenance;
- destination trust;
- sensitivity;
- privilege;
- artifact lineage.

Ablation results measure the contribution of policy signals under the tested benchmark. They do not establish causal importance outside that environment.

## Failure taxonomy

Every observed Flight Recorder attack success is classified after the primary metrics are frozen as one of:

- policy gap;
- metadata/provenance gap;
- tool-mapping or integration gap;
- benchmark/evaluator semantics;
- model trajectory behavior;
- unresolved.

Post-hoc failure analysis must not alter the recorded primary result.

## Reproducibility record

Every experimental run retained as evidence records, where available:

- repository commit;
- release/tag if applicable;
- AgentDojo version;
- manifest contents/hash;
- workflow revision;
- attack name;
- review policy;
- non-secret model deployment identifier;
- raw per-case results;
- policy audit logs;
- GitHub Actions run ID;
- artifact digest.

## Threats to validity

### Internal validity

Model nondeterminism can change trajectories across paired or repeated executions. Policy tuning against observed benchmark failures can create overfitting. Incorrect tool metadata can change enforcement independently of the underlying policy logic.

### Construct validity

AgentDojo attack success measures completion of its defined injection objectives. It is not equivalent to all forms of agent compromise or prompt injection.

### External validity

Results from one benchmark suite, attack family, model deployment, and tool environment may not transfer to other agents or production systems.

### Statistical validity

Thirty holdout pairs provide limited precision, especially when attack success is rare. Zero observed successes must never be interpreted as proof of a zero population attack rate.

## Stopping and amendment rules

The confirmatory holdout stops after all declared pairs have produced valid baseline and Flight Recorder outcomes, unless infrastructure failure prevents completion.

Invalid/incomplete cases are reported and rerun only under a documented infrastructure-recovery rule. Cases may not be silently removed because their results are unfavorable.

Any change to this protocol before holdout execution must be committed as a numbered amendment. Any change after outcomes have been inspected must be labeled post-hoc and cannot redefine the original confirmatory hypothesis.

## Permitted claim boundary

A successful holdout can support a statement of this form:

> Under the recorded AgentDojo, model, attack, and policy conditions, Agent Flight Recorder reduced observed prompt-injection attack success relative to the paired baseline.

It cannot support claims of universal prompt-injection prevention, general security across models or tools, or a zero attack-success probability outside the evaluated sample.
