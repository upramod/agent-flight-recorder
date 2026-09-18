# USENIX Security 2027 Cycle 2 registration sheet

Prepared: 2026-09-17

Use this sheet when the Cycle 2 HotCRP site opens. The CFP currently lists only the Cycle 1 submission-site link, so Cycle 2 registration cannot be completed yet.

## Fixed title

Agent Flight Recorder: Trajectory-Aware Runtime Enforcement for Tool-Using AI Agents

## Fixed author list

Pramod Ubbala

Affiliation for author profile/submission metadata: Independent Researcher, Washington, USA

ORCID: REQUIRED in HotCRP before submission. Enter the author's actual ORCID; do not invent one.

## Tentative non-blank abstract

Tool-using language-model agents can convert untrusted text into external actions. A malicious instruction entering through a document, email, calendar entry, or tool result may influence a later tool call even when the final call appears locally ordinary. We present Agent Flight Recorder, a runtime enforcement layer that evaluates observable tool proposals before execution. The mechanism uses trusted action metadata, successful executed history, destination trust, sensitivity, privilege, and declared artifact lineage. It returns Allow, Review, or Block without reading or storing private chain-of-thought. We evaluated a frozen configuration in a preregistered 120-pair AgentDojo workspace study using the tool_knowledge attack. The paired baseline recorded 20/120 attack successes (16.7%), while Agent Flight Recorder recorded 0/120 (0.0%). The exact two-sided McNemar p-value was 1.91e-06. The security effect carried a substantial utility cost under the confirmatory non-interactive Review=deny policy: legitimate-task success fell from 61/120 (50.8%) to 35/120 (29.2%), with 29 baseline-success/Recorder-failure pairs versus 3 in the opposite direction. A post-hoc sensitivity study on already-seen cases suggests that review handling accounts for much of this loss, but that study does not replace the confirmatory result. Under the recorded benchmark, model, attack, metadata, and policy conditions, trajectory-aware tool-boundary enforcement reduced observed attack completion while imposing a material intervention cost.

## Topics

The USENIX Security 2027 CFP lists both System security and Security of ML as symposium topics.

Recommended selections when the Cycle 2 form opens:
- Security of ML
- System security

Do not finalize topics until the actual Cycle 2 HotCRP taxonomy is visible because the registered topics are fixed after the registration deadline.

## Anonymous artifact

https://anonymous.4open.science/r/agent-flight-recorder-71F8/

Conference anonymization ID: SEC27

## Frozen build

- final manuscript build run: 35305491175
- manuscript source commit: bc11e41f1aab8e85a50a9a4aa5c55499bddb0658
- final preparation branch: submission-usenix-security27-candidate
- PDF artifact digest: sha256:528cb9c7a2dd0896096871cce4252de4ae3f0bae428f8b88c87db645e2f07e1c
- page count: 6
- anonymity check: passed

## Deadlines, AoE

- mandatory registration: January 19, 2027
- paper submission: January 26, 2027
- artifact freeze/deadline: January 29, 2027

The fixed title, full author list including ORCID(s), tentative non-blank abstract, and fixed topics are required at registration. By submission time, each author must have an ORCID in their HotCRP profile and confirm the submission terms.
