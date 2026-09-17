# Submission readiness

Updated: 2026-09-17

## Ready

- Primary v2 result frozen.
- Experimental cycle closed. No v3 is planned to improve observed outcomes.
- Paired utility analysis recorded from the frozen summary.
- USENIX Security 2027 selected as the working submission target.
- Anonymous USENIX LaTeX manuscript created with a vendored style dependency.
- Security and utility results are both stated in the abstract and main results.
- Post-hoc Review evidence is separated from confirmatory evidence.
- V2 is described as 120 previously unused exact pair identities, not 120 wholly novel benchmark primitives.
- Related-work positioning refreshed against current primary sources.
- Bibliography checked against primary/current publication records; MELON metadata corrected to the final publication record.
- Claim-to-evidence audit created.
- Independent statistical verification completed; all primary counts, Wilson intervals, percentage-point differences, paired tables, and exact McNemar p-values match the frozen evidence.
- Reviewer-style risk audit completed.
- Anonymous artifact is built by an allowlist rather than by deleting files from the author repository.
- Anonymous artifact hygiene workflow passed.
- USENIX manuscript compilation has succeeded; the compiled draft is six pages.
- Compiled PDF has been rendered page-by-page and visually inspected with no clipping, overlap, black squares, or broken glyphs observed.
- Reproducibility hashes and run identifiers are retained in the research record.

## Still needed before external submission

1. Obtain a final successful CI build for the latest manuscript revision and retain its PDF artifact.
2. Replace the compact boxed architecture/experiment-flow figures with publication-quality vector figures if they materially improve readability. Do not add unsupported measurements.
3. Create the actual anonymous artifact hosting URL and insert it into the Open Science appendix before submission. Do not link the author-owned public repository in the blinded manuscript.
4. Add the venue-appropriate AI-assistance disclosure in the submission system or manuscript location required by the final venue policy. State the actual use of AI in drafting/editing and technical assistance; do not imply that AI produced benchmark observations.
5. Perform final human author review of the PDF and artifact contents.
6. After final author review, freeze a dedicated submission commit/tag and record the compiled PDF/artifact hashes.

## Paper framing

Frame the work as a systems-security paper about runtime enforcement semantics plus paired benchmark evidence, not as a new universal prompt-injection defense category.

The central result must remain visible in every submission version:

- attack success: 20/120 baseline versus 0/120 Recorder;
- exact paired p=1.91e-06;
- utility: 61/120 baseline versus 35/120 Recorder;
- utility discordance: 29 versus 3;
- confirmatory Review policy: `deny`.

## Stop rule

Do not run a new benchmark because a reviewer might prefer a better utility number. New experimental work should begin only when a target venue reviewer, editor, or separately motivated research question identifies a specific gap that cannot be answered from the frozen evidence.
