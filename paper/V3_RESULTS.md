# Reviewer validation: initial v3 results

Run 37549518814, commit `4dc19b3b92ef1119596d384da49efa1a9896a1c3`. Model: `gpt-4.1-mini-2025-04-14`. Fixed and clean workloads completed without missing cells. Adaptive execution is incomplete. Model-b was not run.

| Outcome | Baseline | Point-only | Full history |
| --- | ---: | ---: | ---: |
| Fixed attack completion | 5/28 | 4/28 | 0/28 |
| Legitimate task success under fixed attack | 13/28 | 15/28 | 11/28 |
| Clean task success | 31/40 | 30/40 | 16/40 |
| Clean tasks with a policy denial | 0/40 | 3/40 | 19/40 |
| Clean policy-denied calls | 0 | 3 | 34 |

Full history versus point-only gives four fewer successful attacks, none reversed, spanning two injection goals and four user tasks. The goal-cluster 20,000-replicate percentile sensitivity interval for the 14.3-percentage-point reduction extends from 0 to 35.7 points. This small exploratory sample does not establish broad superiority.

Clean utility drops 35 points relative to point-only, with 14 tasks lost and none gained. The paired user-bootstrap sensitivity interval is a 20-to-50-point loss. Against baseline, full history loses 15 of 31 baseline-successful tasks (48.4%), with no reverse gains. Point-only loses two and gains one. Paired observations do not prove the cause of each failure.

The full-history audit records 34 denied clean calls. Twenty-eight carry the reason `untrusted input is followed by sensitive-data access`. Denied tools include email searches, file searches, file creation and calendar creation. A policy label alone does not prove each denial caused a scored failure.

## Incomplete adaptive execution

Seven of 84 campaigns completed; 77 are errors, not resistance. Each of four shards encountered HTTP429. The initial conservative guard charged unknown usage against the remaining budget, preventing later calls. Four campaign errors were parser errors. No adaptive rate comparison is justified.

The [recovery amendment](v3-adaptive-recovery-amendment.md) retains this run and starts an all-campaign replication with serial execution, pacing, and logged HTTP429 retries. It neither selects cases by outcome nor merges favorable results. [Recovery run](https://github.com/upramod/agent-flight-recorder/actions/runs/37564751441).

## Audit and remaining work

All 14 archive SHA256 digests match GitHub metadata. Local reanalysis reproduces all CI outcome analyses and counts. Exception paths differ only by local versus CI directories.

- [Full analysis](results/v3-initial-analysis.json)
- [Artifact hashes](results/v3-initial-artifacts.json)
- [Frozen design](reviewer-validation-protocol-v3.md)

The seven-page manuscript includes completed findings and labels adaptive evidence incomplete. It remains a research draft, not a camera-ready submission. A verified second deployment is still required. We have not tuned policy after seeing these outcomes.
