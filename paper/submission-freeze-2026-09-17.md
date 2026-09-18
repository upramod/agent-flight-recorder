# USENIX Security 2027 submission preparation freeze

Date: 2026-09-17

This record freezes the prepared submission state after the confirmatory experiment, manuscript audit, independent statistical verification, successful anonymous PDF build, and AI-assistance disclosure.

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

## Build evidence

Successful anonymous manuscript build:
- GitHub Actions run: 35274572555
- build commit: fb1f26f831e499f627e32b73e4b1b72e9b9c3008
- compiled manuscript: 6 pages
- artifact: usenix-security-2027-draft-35274572555
- artifact digest: sha256:ef2a09b4f817334127b354b752931aad030863d6bb14e6693044a5b0cfde08f2
- anonymity check: passed
- bibliography build: passed

## Submission boundary

The paper is prepared for USENIX Security 2027 Cycle 2. External submission is not complete.

Before submission:
1. Human author reviews the complete PDF and accepts responsibility for all content.
2. Upload the allowlisted anonymous artifact bundle to a non-tracking anonymous host, preferably anonymous.4open.science using conference ID SEC27.
3. Replace the Open Science appendix placeholder with the final anonymous artifact URL.
4. Rebuild and re-run anonymity checks.
5. Register the fixed title, author list, ORCIDs, abstract, and topics by the venue registration deadline.
6. Submit the final PDF only after the human author confirms the submission terms.

Do not use the public author repository as the review artifact because it reveals identity.
