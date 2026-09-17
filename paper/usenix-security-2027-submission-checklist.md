# USENIX Security 2027 Cycle 2 submission checklist

Prepared: 2026-09-17

## Fixed venue requirements

- Mandatory registration: January 19, 2027, AoE.
- Paper deadline: January 26, 2027, AoE.
- Artifact deadline: January 29, 2027, AoE.
- Main body: at most 13 pages.
- Format: USENIX Security template, U.S. letter, two columns, 10-point Times Roman on 12-point leading.
- Review: anonymous. No author names, affiliations, identifying acknowledgments, repository owner names, or identifying artifact URLs.
- Open Science appendix: required.
- Ethics appendix: strongly encouraged.
- Artifact link: anonymous, non-tracking, and available through the review period.
- Registration requires fixed title, fixed author list, ORCIDs, tentative non-blank abstract, and fixed topics.

Official sources:

- https://www.usenix.org/conference/usenixsecurity27/call-for-papers
- https://www.usenix.org/conferences/author-resources/paper-templates

## Manuscript status

- [x] Frozen v2 primary result recorded.
- [x] Security endpoint reported as paired data.
- [x] Utility endpoint reported as paired data.
- [x] Confirmatory and post-hoc evidence separated.
- [x] Universal-security wording removed.
- [x] Adaptive robustness listed as unmeasured.
- [x] Trusted metadata identified as a security boundary.
- [x] Anonymous USENIX LaTeX source created at `paper/usenix-security-2027.tex`.
- [x] Ethical Considerations appendix drafted.
- [x] Open Science appendix drafted.
- [x] Bibliography source created.
- [ ] Compile with the official USENIX style file and inspect page count.
- [ ] Verify every bibliography entry against its primary publication page.
- [ ] Inspect every figure and table in grayscale.
- [ ] Remove any author identity from PDF metadata.
- [ ] Run a repository-wide anonymity scan on the artifact bundle.
- [ ] Create anonymous artifact mirror using conference ID `SEC27`.
- [ ] Replace the Open Science placeholder text with the final anonymous artifact URL.
- [ ] Confirm anonymous artifact URL has no analytics or access tracking.
- [ ] Register paper in HotCRP before January 19, 2027 AoE.
- [ ] Confirm every author has ORCID in HotCRP.
- [ ] Freeze title and author list at registration.
- [ ] Human author performs line-by-line technical review of final PDF.
- [ ] Human author checks every result against the frozen evidence files.
- [ ] Human author checks every citation against the cited paper.
- [ ] Submit paper by January 26, 2027 AoE.
- [ ] Freeze and submit artifact by January 29, 2027 AoE.

## Current fixed title

**Agent Flight Recorder: Trajectory-Aware Runtime Enforcement for Tool-Using AI Agents**

Do not change the registered title after the mandatory registration deadline unless the venue explicitly permits it.

## Evidence values that must not drift

- V2 pairs: 120.
- Baseline attack success: 20/120.
- Recorder attack success: 0/120.
- Attack McNemar p-value: 1.90735e-06.
- Baseline utility: 61/120.
- Recorder utility: 35/120.
- Utility paired discordance: 29 baseline-success/Recorder-failure versus 3 in the opposite direction.
- Utility McNemar p-value: 2.55601e-06.
- Confirmatory review behavior: `Review=deny`.
- Successful workflow run: 35180860582.
- Generated v2 manifest SHA-256: `133014deda3d84607e29270525fce26e45b3f75b2b4f94559135c373f4b1b3aa`.
- Successful artifact SHA-256: `3a4e8c97a8237b8f2fa5eae08f9fc2e4188c72173ff594a58680b7b907faac81`.

No new benchmark run should replace these values inside the confirmatory narrative.
