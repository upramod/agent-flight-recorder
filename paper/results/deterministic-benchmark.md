# Deterministic benchmark results

Run date: 2026-09-15  
Repository commit: `fb8b40d809babb43a33b3e06014d11ee29049c13`  
Node.js: v24.19.0  
Platform: Linux 6.18.44  
Trace version: 0.1.0

## Validation

`npm test` passed 40 of 40 tests.

The benchmark used 10 unique traces and five enforcement strategies. Each trace-strategy pair ran 100 times for local timing, producing 5,000 JSONL rows. Security and utility counts use each unique trace once. Timing repetitions are not independent security samples.

## Results

| Strategy | Unsafe execution | False block | Reviews | Review denied | Executor failures | Sensitivity accuracy | Median trace ms | p95 trace ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no_gate | 7/7 (100.0%) | 0/21 (0.0%) | 0 | 0 | 1 | N/A | 0.0105 | 0.0198 |
| point_action | 7/7 (100.0%) | 0/21 (0.0%) | 2 | 1 | 1 | N/A | 0.0201 | 0.0441 |
| session_heuristic | 4/7 (57.1%) | 1/21 (4.8%) | 3 | 1 | 1 | N/A | 0.0362 | 0.0818 |
| artifact_aware | 0/7 (0.0%) | 0/21 (0.0%) | 2 | 1 | 1 | 10/10 (100.0%) | 0.0399 | 0.1091 |
| human_review_only | 7/7 (100.0%) | 0/21 (0.0%) | 7 | 1 | 1 | N/A | 0.0101 | 0.0178 |

## Reading the table

The artifact-aware strategy prevented all seven labeled unsafe actions in this corpus and preserved all 21 labeled benign actions from policy blocking. The session heuristic prevented three unsafe actions but blocked one benign action because unrelated restricted activity contaminated the session-wide decision. Point-action and human-review-only strategies executed all seven unsafe actions under the scripted approvals.

These exact counts describe the fixed synthetic corpus. They do not estimate performance on a broader workload population. The latency values measure in-process synthetic traces and exclude model calls, network time, tool latency, and human review.

## Reproduction

```bash
npm test
npm run benchmark -- --repetitions 100 --output results/benchmark.jsonl
npm run benchmark:summary
```

The raw JSONL contains action decisions, execution outcomes, safety labels, effective sensitivity, source IDs, and timing for every trace-strategy repetition.
