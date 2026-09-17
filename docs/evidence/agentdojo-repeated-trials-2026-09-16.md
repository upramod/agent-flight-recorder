# AgentDojo repeated-trials evidence

**Status:** post-hoc repeated-run variance study. Not confirmatory evidence.  
**Date:** 2026-09-16  
**Run:** `35167246091`  
**Run commit:** `7009c73db2463f03386ee2f12ada5d099a659f1f`  
**Artifact:** `agentdojo-repeated-35167246091`  
**Artifact SHA-256:** `7b710093a9adb8993a91e7f0742c931fa3d219b6300dac4e12c0a55877929b88`

This experiment repeats the same already-seen 30 holdout pair identities five times under three fixed conditions: baseline, Agent Flight Recorder with `Review=deny`, and Agent Flight Recorder with `Review=approve`. It uses AgentDojo v1.2.2, the workspace suite, the `tool_knowledge` attack, the same trusted domain, and the same Azure deployment. The condition order rotates across the five blocks to reduce a fixed ordering effect.

The 30 pair identities are repeated in every block. The resulting 150 observations per condition are therefore not 150 independently sampled benchmark tasks.

## Aggregate result

| Condition | Attack success | Utility | Mean attack rate across blocks (SD) | Mean utility across blocks (SD) |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 1/150 | 113/150 | 0.7% (1.5 percentage points) | 75.3% (3.0 pp) |
| Flight Recorder, Review=deny | 0/150 | 74/150 | 0.0% (0.0 pp) | 49.3% (1.5 pp) |
| Flight Recorder, Review=approve | 0/150 | 115/150 | 0.0% (0.0 pp) | 76.7% (2.4 pp) |

## Per-block results

| Block | Baseline utility | Baseline attack success | Deny utility | Deny attack success | Approve utility | Approve attack success |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 22/30 | 1/30 | 15/30 | 0/30 | 23/30 | 0/30 |
| 2 | 22/30 | 0/30 | 14/30 | 0/30 | 22/30 | 0/30 |
| 3 | 24/30 | 0/30 | 15/30 | 0/30 | 23/30 | 0/30 |
| 4 | 23/30 | 0/30 | 15/30 | 0/30 | 24/30 | 0/30 |
| 5 | 22/30 | 0/30 | 15/30 | 0/30 | 23/30 | 0/30 |

## What the repeated runs show

The main run-to-run variation is in legitimate-task utility, not observed attack success. Baseline utility ranged from 22/30 to 24/30. Review=deny utility stayed between 14/30 and 15/30. Review=approve utility ranged from 22/30 to 24/30.

Review=deny reproduced the utility penalty seen in the preregistered holdout. Across all five repeated blocks it averaged 49.3% utility, roughly 26 percentage points below the baseline block mean.

Review=approve recovered that utility loss in this repeated study. Its mean utility was 76.7%, close to the baseline mean of 75.3%. This is consistent with the earlier single sensitivity run, but it remains post-hoc evidence because the pair identities were already known.

No Flight Recorder attack success was observed in either Review mode across the five repeated blocks. The baseline produced one observed attack success across the same five blocks. This does not establish a zero underlying attack probability for either Flight Recorder configuration.

## Interpretation boundary

The preregistered holdout remains the primary unseen-case result. This repeated study estimates stochastic behavior on the same 30 already-seen pair identities and characterizes the Review-handling tradeoff.

A supported descriptive statement is:

> Across five repeated executions of the same 30 AgentDojo holdout pairs, Review=deny maintained zero observed attack successes but imposed a persistent utility penalty, while Review=approve recovered utility to approximately the baseline level and also recorded zero observed attack successes in these repeated runs.

This evidence does not justify a universal security claim, does not convert repeated observations into independent tasks, and does not by itself authorize changing the frozen production policy.
