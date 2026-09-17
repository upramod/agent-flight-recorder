from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("Usage: analyze_repeated_trials.py INPUT_CSV OUTPUT_JSON OUTPUT_MD")
    rows = list(csv.DictReader(Path(sys.argv[1]).open()))
    grouped: dict[str, dict[int, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"utility": 0, "attack_success": 0, "n": 0}))
    for row in rows:
        condition = row["condition"]
        block = int(row["block"])
        grouped[condition][block]["utility"] += int(row["utility"])
        grouped[condition][block]["attack_success"] += int(row["attack_success"])
        grouped[condition][block]["n"] += 1

    result = {}
    for condition in ("baseline", "deny", "approve"):
        blocks = grouped[condition]
        if set(blocks) != set(range(1, 6)) or any(v["n"] != 30 for v in blocks.values()):
            raise ValueError(f"Incomplete repeated trials for {condition}")
        attack_rates = [blocks[i]["attack_success"] / 30 for i in range(1, 6)]
        utility_rates = [blocks[i]["utility"] / 30 for i in range(1, 6)]
        result[condition] = {
            "blocks": [blocks[i] for i in range(1, 6)],
            "attack_success_total": sum(blocks[i]["attack_success"] for i in range(1, 6)),
            "utility_total": sum(blocks[i]["utility"] for i in range(1, 6)),
            "observations": 150,
            "attack_rate_block_mean": statistics.mean(attack_rates),
            "attack_rate_block_min": min(attack_rates),
            "attack_rate_block_max": max(attack_rates),
            "attack_rate_block_sd": statistics.stdev(attack_rates),
            "utility_rate_block_mean": statistics.mean(utility_rates),
            "utility_rate_block_min": min(utility_rates),
            "utility_rate_block_max": max(utility_rates),
            "utility_rate_block_sd": statistics.stdev(utility_rates),
        }

    Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# Repeated-trials aggregate", "", "Five blocks, 30 fixed pair identities per condition per block.", "", "| Condition | Attack success | Utility | Attack block mean (SD) | Utility block mean (SD) |", "| --- | ---: | ---: | ---: | ---: |"]
    for condition in ("baseline", "deny", "approve"):
        r = result[condition]
        lines.append(
            f"| {condition} | {r['attack_success_total']}/150 | {r['utility_total']}/150 | "
            f"{100*r['attack_rate_block_mean']:.1f}% ({100*r['attack_rate_block_sd']:.1f} pp) | "
            f"{100*r['utility_rate_block_mean']:.1f}% ({100*r['utility_rate_block_sd']:.1f} pp) |"
        )
    lines.extend(["", "These 150 observations per condition reuse 30 pair identities across five blocks. They are not 150 independently sampled benchmark tasks."])
    Path(sys.argv[3]).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
