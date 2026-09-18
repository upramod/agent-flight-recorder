# USENIX Security 2027 submission preparation freeze

Date: 2026-09-17

This record freezes the prepared submission state after the confirmatory experiment, manuscript audit, independent statistical verification, successful anonymous PDF build, AI-assistance disclosure, and reviewer-facing anonymous artifact creation.

## Scientific result

- Confirmatory v2: 120 previously unused exact AgentDojo pair identities.
- Baseline attack success: 20/120.
- Agent Flight Recorder attack success: 0/120.
- Exact two-sided McNemar p = 1.9073486328125e-06.
- Baseline utility: 61/120.
- Recorder utility: 35/120.
- Utility discordance: 29 baseline-success/Recorder-failure versus 3 in the opposite direction.
- Exact two-sided utility McNemar p = 2.5560148060321808e-06.
- Confirmatory Review policy: deny.
- No v3 experiment is authorized to improve observed results.

## Final anonymous build evidence

- GitHub Actions run: 35305491175
- manuscript commit: bc11e41f1aab8e85a50a9a4aa5c55499bddb0658
- compiled manuscript: 6 pages
- artifact: usenix-security-2027-draft-35305491175
- artifact digest: sha256:528cb9c7a2dd0896096871cce4252de4ae3f0bae428f8b88c87db645e2f07e1c
- anonymity check: passed
- bibliography build: passed
- artifact upload: passed

## Anonymous review artifact

Reviewer-facing root:

https://anonymous.4open.science/r/agent-flight-recorder-71F8/

The anonymous repository was created through anonymous.4open.science using the source repository. The reviewer-facing page was manually checked in the anonymous presentation and displayed the anonymized repository name `agent-flight-recorder-71F8` with no visible author identity in the repository root/README view.

The Open Science appendix now contains this anonymous root URL.

## AI-assistance record

See `paper/ai-assistance-disclosure.md`. Generative AI assistance was used for drafting/editing, technical review, repository/CI scripting, and presentation checks. Experimental observations came from the recorded benchmark workflows and the reported statistics were independently recomputed from frozen evidence.

## Submission boundary

The research and submission package are frozen. External USENIX submission is not yet complete.

The remaining venue actions are administrative:
1. Human author reviews the final PDF and accepts responsibility for all submitted content.
2. Ensure the anonymous artifact remains accessible through the full review period.
3. Register the fixed title, fixed author list including ORCID(s), tentative non-blank abstract, and fixed topics by January 19, 2027 (AoE).
4. Submit the PDF by January 26, 2027 (AoE).
5. Ensure submission artifacts are final by January 29, 2027 (AoE).
6. All authors must confirm the submission terms in HotCRP by submission time.

Do not update the frozen experiment or change the anonymous artifact after the venue artifact freeze merely to improve observed results.
