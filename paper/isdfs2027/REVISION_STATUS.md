# ISDFS 2027 Paper 107: revision status

Updated October 7, 2026 UTC (October 6 Pacific). This is a working revision, not a completed camera-ready submission. Detailed findings and the proposed next experiment are in [DEEP_REVIEW.md](DEEP_REVIEW.md).

## New live experiments

The [v3 results](../V3_RESULTS.md) supersede earlier statements below that no clean or point-only comparison exists. All 84 fixed cells and 120 clean cells completed on verified gpt-4.1-mini-2025-04-14. Fixed attack counts were 5/28 baseline, 4/28 point-only, 0/28 full history. Clean utility was 31/40, 30/40, 16/40. The history gain spans only two attack goals and carries a large clean-task cost.

Initial adaptive execution is incomplete (7/84 completed); HTTP429 triggered budget stops. The retained recovery run ended with 48/84 valid campaigns and 36 errors. Its legacy-loader outcomes cannot establish literal-payload robustness. A first corrected run failed before experiments; repaired run 37571375916 passed CI and is executing. See the current results note for full provenance. No second model is available. The manuscript is seven pages and is not camera-ready.

## Historical deep-review checkpoint

## Completed work and corrections

- Recovered the submitted IEEE source and original 120-pair archive, SHA-256 `3a4e8c97a8237b8f2fa5eae08f9fc2e4188c72173ff594a58680b7b907faac81`.
- Verified all 240 raw primary endpoints against the summary and equality of paired injected payloads. Attack completion remains 20/120 versus 0/120; utility under attack remains 61/120 versus 35/120, with 29 lost and three gained pairs.
- Corrected the initial October diagnostic analysis, which combined auxiliary injection-task runs with attacked user-task runs. A validated extractor separates sessions using raw transcripts, timestamps, tool sequence, successful-history lengths, and execution status.
- Main-task accounting is 306 proposals: 182 Allow, 108 Review, 16 Block; 160 successful effects, 22 allowed execution failures, 124 policy denials. Excluded 249 auxiliary proposals. The earlier 555-proposal totals must not describe the 120 attacked trajectories.
- Replayed all 306 attacked-run proposals with zero score or decision mismatches. Added five signal ablations and nine threshold conditions. Execution membership/order remains fixed, with ablated metadata transformed in past successful actions. These are decision diagnostics, not counterfactual task outcomes.
- Corrected utility-loss interpretation. First main-task intervention: calendar creation Review in eight, file deletion Review in five, file creation Review in three, unread-email retrieval Review in two, email Block in two, and three other operations in one each. Six lost pairs had no policy intervention. These are associations, not causal assignments.
- Exactly reproduced the metadata-corruption study and corrected its method: one draw per trace downgrades all sensitive source labels.
- Repaired normalization before argument assessment in the AgentDojo adapter and propagated External provenance through artifact lineage. Added targeted regressions. These are post-study repairs, not changes to historical v2 outcomes or evidence that the repaired code has been live-benchmarked.
- Checked primary research sources, added Progent and Fides, updated CaMeL to IEEE SaTML 2026, and corrected the pinned AgentArmor title. The paper does not claim novelty for deterministic gating or taint propagation alone.
- Narrowed live claims to session-history enforcement. The integration emits no artifact lineage; no live point-only baseline establishes incremental history benefit. Twelve of fourteen injection goals involve email, which point metadata can already deny.
- Removed the p-value from the abstract, labeled pair-level inference nominal, disclosed 38 user-task and 14 injection-task components, and identified the unreported paired-effect interval required by v2.
- Validation: 59 repository tests, 13 pinned AgentDojo adapter tests, and eight archive-extraction tests pass. A six-page IEEE PDF was built and visually checked; no overfull boxes or unresolved citations. Ordinary underfull justification notices remain.

## Reviewer requests and open evidence gaps

| Request | Current response | Remaining limit |
| --- | --- | --- |
| Threshold justification or ablation | Nine-condition post-hoc sweep and explicit weight semantics | No optimality or outcome-level recovery claim |
| Metadata-feature ablation | Five removals on validated attacked sessions | Fixed execution history; no counterfactual rerun or live lineage ablation |
| Trusted metadata assumptions | Corruption tests, normalization repair, explicit coverage limits | Recipient fields, runtime validation, and resource authorization remain incomplete |
| Utility loss | Corrected main-run accounting and lost-pair diagnostics | No clean-workload control or complete causal decomposition |
| Different models | Not completed | No verified second deployment or underlying historical model snapshot |
| Wider and adaptive attacks | Not completed | One frozen attack family; policy-aware feedback-budgeted evaluation required |
| Trajectory contribution | Explicitly bounded | Needs a live same-metadata point-only comparator |

At the earlier deep-review checkpoint, no new model experiment had been run. The source identifies remaining synchronous-gate, malformed-metadata, and incomplete-lineage assurance limits. The revision is not a complete empirical response to all requested validation.

## Reproduction

Use locked Node dependencies and Python 3. The adapter suite also requires the pinned AgentDojo dependencies. Run from the repository root:

```sh
npm ci
npm test
python -m unittest test.test_attacked_audits
python -m unittest discover -s integrations/agentdojo -p test_executor.py
python scripts/extract_attacked_audits.py PATH_TO_ORIGINAL_WORKFLOW_ARCHIVE.zip /tmp/afr-attacked-audits
node scripts/reviewer_policy_replay.mjs /tmp/afr-attacked-audits paper/results/reviewer-policy-replay-2026-10-06.json
python scripts/reviewer_utility_diagnostics.py PATH_TO_ORIGINAL_WORKFLOW_ARCHIVE.zip paper/results/reviewer-utility-diagnostics-2026-10-06.json
node dist/metadataErrorStudy.js --trials 1000 --seed 20260916 --output reproduced-metadata.json
```

Use a new extraction directory. Do not replay the original mixed-session JSONL files directly; replay now rejects multi-session or unidentified files. The archive is retained in the submitted package's `verified-evidence` directory. No model credentials are needed for these diagnostics.

Build the manuscript from this directory using pdflatex, bibtex, and two more pdflatex passes. The source is `Agent_Flight_Recorder_ISDFS_2027.tex`. The submitted package and original benchmark attribution remain unchanged.

## Conference requirements

Official format: https://www.isdfs.org/2027/paper-format/ . Maximum six pages, IEEE two-column, 10-point, named authors.

Deadline conflict: the October 6 acceptance email says February 25, 2027 for camera-ready and registration. The checked official format page says February 15, 2027 for camera-ready. Use February 15 as the internal completion target until resolved. Registration remains February 25 in the acceptance email.

The official page gives PDF eXpress ID 73487X and the general copyright notice `979-8-3195-4011-9/27/$31.00 ©2027 IEEE`. Apply the appropriate notice during final preparation. PDF eXpress certification, registration, camera-ready upload, and the IEEE copyright form remain pending.
