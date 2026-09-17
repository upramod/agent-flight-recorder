from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


CONDITIONS = ("baseline", "flight-recorder-deny", "flight-recorder-approve")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    return parser.parse_args()


def find_summaries(root: Path) -> list[dict]:
    summaries = []
    for path in sorted(root.rglob("repeat-summary.json")):
        summaries.append(json.loads(path.read_text(encoding="utf-8")))
    if len(summaries) != 5:
        raise ValueError(f"Expected five repeat summaries, found {len(summaries)}")
    repeats = sorted(int(summary["repeat"]) for summary in summaries)
    if repeats != [1, 2, 3, 4, 5]:
        raise ValueError(f"Expected repeat IDs 1..5, got {repeats}")
    return sorted(summaries, key=lambda item: int(item["repeat"]))


def descriptive(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.mean(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def main() -> None:
    options = arguments()
    summaries = find_summaries(options.root)

    result: dict[str, object] = {
        "repetitions": len(summaries),
        "pairsPerRepetition": 30,
        "conditions": {},
        "perRepeat": summaries,
    }

    condition_stats: dict[str, dict[str, object]] = {}
    for condition in CONDITIONS:
        utility_rates = [float(summary["aggregates"][condition]["utilityRate"]) for summary in summaries]
        attack_rates = [float(summary["aggregates"][condition]["attackSuccessRate"]) for summary in summaries]
        utility_counts = [int(summary["aggregates"][condition]["utility"]) for summary in summaries]
        attack_counts = [int(summary["aggregates"][condition]["attackSuccess"]) for summary in summaries]
        condition_stats[condition] = {
            "utilityCounts": utility_counts,
            "attackSuccessCounts": attack_counts,
            "utilityRate": descriptive(utility_rates),
            "attackSuccessRate": descriptive(attack_rates),
        }
    result["conditions"] = condition_stats

    differences = []
    for summary in summaries:
        baseline = summary["aggregates"]["baseline"]
        deny = summary["aggregates"]["flight-recorder-deny"]
        approve = summary["aggregates"]["flight-recorder-approve"]
        differences.append(
            {
                "repeat": int(summary["repeat"]),
                "denyAttackSuccessMinusBaseline": int(deny["attackSuccess"]) - int(baseline["attackSuccess"]),
                "approveAttackSuccessMinusBaseline": int(approve["attackSuccess"]) - int(baseline["attackSuccess"]),
                "denyUtilityMinusBaseline": int(deny["utility"]) - int(baseline["utility"]),
                "approveUtilityMinusBaseline": int(approve["utility"]) - int(baseline["utility"]),
                "approveUtilityMinusDeny": int(approve["utility"]) - int(deny["utility"]),
            }
        )
    result["perRepeatDifferences"] = differences

    options.json.parent.mkdir(parents=True, exist_ok=True)
    options.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Repeated AgentDojo stochastic evaluation",
        "",
        "**Status:** post-hoc variance study on already-seen holdout pairs. Not confirmatory evidence.",
        "",
        "Five repetitions were run over the same 30 pair identities under baseline, Flight Recorder Review=deny, and Flight Recorder Review=approve conditions.",
        "",
        "## Per-repetition results",
        "",
        "| Repeat | Baseline utility | Baseline attacks | Deny utility | Deny attacks | Approve utility | Approve attacks |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for summary in summaries:
        a = summary["aggregates"]
        lines.append(
            f"| {summary['repeat']} | {a['baseline']['utility']}/30 | {a['baseline']['attackSuccess']}/30 | "
            f"{a['flight-recorder-deny']['utility']}/30 | {a['flight-recorder-deny']['attackSuccess']}/30 | "
            f"{a['flight-recorder-approve']['utility']}/30 | {a['flight-recorder-approve']['attackSuccess']}/30 |"
        )

    lines.extend(["", "## Across-run variation", ""])
    for condition in CONDITIONS:
        stats = condition_stats[condition]
        u = stats["utilityRate"]
        a = stats["attackSuccessRate"]
        lines.append(
            f"- **{condition}**: utility mean {u['mean']:.1%}, SD {u['stdev']:.1%}, range {u['min']:.1%} to {u['max']:.1%}; "
            f"attack-success mean {a['mean']:.1%}, SD {a['stdev']:.1%}, range {a['min']:.1%} to {a['max']:.1%}."
        )

    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "These repeated observations estimate run-to-run variation for the same already-seen 30 AgentDojo pairs. They are not 150 independent tasks per condition and do not replace the preregistered holdout. Zero observed attacks in a condition does not establish a zero underlying attack probability.",
            "",
        ]
    )
    options.markdown.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
