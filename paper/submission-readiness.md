# Submission readiness

Updated: 2026-09-17

## Ready

- Primary v2 result frozen.
- Experimental cycle closed. No v3 is planned to improve observed outcomes.
- Paired utility analysis recorded from the frozen summary.
- Manuscript recentered on the 120-pair AgentDojo result.
- Security and utility results are both stated in the abstract and main results.
- Post-hoc Review evidence is separated from confirmatory evidence.
- Related-work positioning refreshed against current primary sources.
- Claim-to-evidence audit created.
- Reproducibility hashes and run identifiers appear in the manuscript.

## Still needed before external submission

1. Select a target venue or preprint format and convert the Markdown draft to its template.
2. Create publication-quality figures from the architecture and experiment flow. Figures must not add unsupported measurements.
3. Verify bibliography formatting against the selected venue and replace preprint citations with final proceedings versions where available.
4. Perform one line-by-line technical review against repository code and frozen evidence.
5. Perform one independent statistical check of all reported counts, intervals, and p-values.
6. Add an artifact-availability statement with the public repository and release/tag chosen for the paper.
7. Add an AI-assistance disclosure that matches the selected venue's current policy. The disclosure should state the actual use of AI in drafting/editing and technical assistance. It should not imply that AI produced experimental observations that came from the recorded benchmark workflow.
8. Freeze the submission manuscript at a dedicated commit and tag after final author review.

## Recommended paper framing

The strongest framing is a systems-security paper about runtime enforcement semantics plus paired benchmark evidence. The paper is weaker if framed as a claim of a new universal prompt-injection defense.

The central result should remain visible in every submission version:

- attack success: 20/120 baseline versus 0/120 Recorder;
- exact paired p=1.91e-06;
- utility: 61/120 baseline versus 35/120 Recorder;
- utility discordance: 29 versus 3;
- confirmatory Review policy: `deny`.

## Stop rule

Do not run a new benchmark because a reviewer might prefer a better utility number. New experimental work should begin only when a target venue reviewer, editor, or separately motivated research question identifies a specific gap that cannot be answered from the frozen evidence.
