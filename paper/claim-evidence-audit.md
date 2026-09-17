# Claim-to-evidence audit

Reviewed: 2026-09-17

## Primary claims

| Manuscript claim | Evidence | Status | Boundary |
|---|---|---|---|
| Agent Flight Recorder recorded 0/120 attack successes versus 20/120 for baseline | `docs/evidence/agentdojo-independent-v2-2026-09-17.md`; run `35180860582`; artifact `agentdojo-v2-35180860582` | Supported | Applies only to recorded AgentDojo v2 conditions |
| Exact paired attack McNemar p=1.90735e-06 | Frozen `analysis.json`, SHA-256 `08d7ec184be607ec4620ccaee2247ca3981a0f834bc5601ca5c93af35af7e9d3` | Supported | Statistical result does not imply universal security |
| Baseline utility was 61/120 and Recorder utility was 35/120 | Frozen `summary.csv`, SHA-256 `a080ec60debde9746fd6e4d2b55ac38bf1900050f48bc609d5ec5b04a860041d` | Supported | Confirmatory condition is `Review=deny` |
| Utility discordance was 29 baseline-success/Recorder-failure versus 3 in the opposite direction; exact McNemar p=2.55601e-06 | `docs/evidence/agentdojo-v2-utility-paired-analysis-2026-09-17.md`, derived directly from frozen `summary.csv` | Supported secondary analysis | Does not alter primary endpoint |
| Review handling accounts for much of the observed utility loss | `docs/evidence/agentdojo-review-approve-sensitivity-2026-09-16.md` and `docs/evidence/agentdojo-repeated-trials-2026-09-16.md` | Supported as post-hoc mechanism evidence | Must not be described as confirmatory or as proof that auto-approval is safe |
| Runtime decisions do not require private chain-of-thought | `README.md`, `src/engine.ts`, `src/gate.ts`, `integrations/agentdojo/flight_recorder_executor.py` | Supported by implementation | Says nothing about model internals beyond not being required by the gate |
| Only successful executions enter causal history | `src/gate.ts`; regression tests | Supported by implementation | Depends on all consequential tools passing through the gate |
| Trusted metadata is part of the security boundary | Adapter implementation plus prior metadata-corruption evidence | Supported | Wrong labels can produce wrong decisions |

## Claims removed or prohibited

The manuscript must not state or imply any of the following:

- zero population attack probability;
- universal prompt-injection prevention;
- production readiness;
- robustness to adaptive attacks;
- utility preservation under the confirmatory policy;
- first runtime trace defense;
- first data-flow defense for tool agents;
- superiority to CaMeL, AgentArmor, MELON, AttriGuard, or firewall defenses without a direct matched comparison;
- 150 repeated known-pair observations as 150 independent benchmark tasks;
- post-hoc `Review=approve` as a replacement for v2 `Review=deny`.

## Provenance anchors

- Protocol v2 commit: `f2ea33d8da9d45fc0c7b66969ef696eb15f5cce5`
- Generator/test commit: `b0e586d550340665b9def0ee9b972a0765cae5bf`
- Parser-only corrections: `c1a02231d8b892bb512cc87357bd35079c729ea9`, `ea13b0007def03efcbd46b22734d91485678646a`
- Successful run commit: `9ef3022fa5dd05ae8746c6f8b4556ad6311e30a5`
- Successful GitHub Actions run: `35180860582`
- Artifact SHA-256: `3a4e8c97a8237b8f2fa5eae08f9fc2e4188c72173ff594a58680b7b907faac81`
- Generated manifest SHA-256: `133014deda3d84607e29270525fce26e45b3f75b2b4f94559135c373f4b1b3aa`
- Frozen summary SHA-256: `a080ec60debde9746fd6e4d2b55ac38bf1900050f48bc609d5ec5b04a860041d`

## Literature-position audit

The manuscript cites prior work that already covers indirect prompt injection, tool-agent benchmarks, trusted control/data flow, trajectory re-execution, runtime trace analysis, tool firewalls, causal attribution, and adaptive attacks. The novelty language therefore stays at the level of this system's specific execution semantics and its paired evidence. No first-of-kind claim is used.
