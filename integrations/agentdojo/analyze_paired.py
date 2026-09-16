from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

Z95 = 1.959963984540054


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    return parser.parse_args()


def wilson(successes: int, total: int) -> tuple[float, float]:
    if total <= 0:
        raise ValueError("Wilson interval requires total > 0")
    p = successes / total
    z2 = Z95 * Z95
    denominator = 1 + z2 / total
    center = (p + z2 / (2 * total)) / denominator
    half = Z95 * math.sqrt((p * (1 - p) + z2 / (4 * total)) / total) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def exact_mcnemar(baseline_only: int, recorder_only: int) -> float:
    discordant = baseline_only + recorder_only
    if discordant == 0:
        return 1.0
    k = min(baseline_only, recorder_only)
    tail = sum(math.comb(discordant, i) for i in range(k + 1)) / (2 ** discordant)
    return min(1.0, 2 * tail)


def load_pairs(path: Path) -> dict[str, dict[str, dict[str, str]]]:
    paired: dict[str, dict[str, dict[str, str]]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            case = row["case"]
            mode = row["mode"]
            if mode not in {"baseline", "flight-recorder"}:
                raise ValueError(f"Unexpected mode {mode!r} for {case}")
            if mode in paired.setdefault(case, {}):
                raise ValueError(f"Duplicate row for {case}/{mode}")
            paired[case][mode] = row
    if not paired:
        raise ValueError("No paired rows found")
    for case, modes in paired.items():
        if set(modes) != {"baseline", "flight-recorder"}:
            raise ValueError(f"Incomplete pair for {case}: {sorted(modes)}")
    return paired


def binary(row: dict[str, str], field: str) -> int:
    value = int(row[field])
    if value not in {0, 1}:
        raise ValueError(f"Expected binary {field}, got {value}")
    return value


def main() -> None:
    options = arguments()
    pairs = load_pairs(options.summary)
    cases = sorted(pairs)

    baseline_attack = sum(binary(pairs[c]["baseline"], "attack_success") for c in cases)
    recorder_attack = sum(binary(pairs[c]["flight-recorder"], "attack_success") for c in cases)
    baseline_utility = sum(binary(pairs[c]["baseline"], "utility_passed") for c in cases)
    recorder_utility = sum(binary(pairs[c]["flight-recorder"], "utility_passed") for c in cases)
    total = len(cases)

    baseline_only = 0
    recorder_only = 0
    both_attack = 0
    neither_attack = 0
    for case in cases:
        b = binary(pairs[case]["baseline"], "attack_success")
        r = binary(pairs[case]["flight-recorder"], "attack_success")
        if b and not r:
            baseline_only += 1
        elif r and not b:
            recorder_only += 1
        elif b and r:
            both_attack += 1
        else:
            neither_attack += 1

    baseline_rate = baseline_attack / total
    recorder_rate = recorder_attack / total
    risk_difference = recorder_rate - baseline_rate
    relative_reduction = None if baseline_rate == 0 else (baseline_rate - recorder_rate) / baseline_rate

    b_ci = wilson(baseline_attack, total)
    r_ci = wilson(recorder_attack, total)
    p_value = exact_mcnemar(baseline_only, recorder_only)

    result = {
        "pairCount": total,
        "attack": {
            "baseline": {
                "successes": baseline_attack,
                "total": total,
                "rate": baseline_rate,
                "wilson95": list(b_ci),
            },
            "flightRecorder": {
                "successes": recorder_attack,
                "total": total,
                "rate": recorder_rate,
                "wilson95": list(r_ci),
            },
            "absoluteRiskDifferenceRecorderMinusBaseline": risk_difference,
            "relativeReduction": relative_reduction,
            "pairedDiscordance": {
                "baselineSuccessRecorderResisted": baseline_only,
                "baselineResistedRecorderSuccess": recorder_only,
                "bothSuccess": both_attack,
                "bothResisted": neither_attack,
            },
            "exactMcNemarTwoSidedP": p_value,
        },
        "utility": {
            "baselineSuccesses": baseline_utility,
            "flightRecorderSuccesses": recorder_utility,
            "total": total,
        },
        "interpretationBoundary": (
            "This analysis applies only to the preregistered paired holdout under the recorded "
            "benchmark, model, attack, metadata, and policy conditions. Zero observed successes, "
            "if present, is not evidence of a zero population attack rate."
        ),
    }

    options.json.parent.mkdir(parents=True, exist_ok=True)
    options.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    rr_text = "undefined (baseline rate is zero)" if relative_reduction is None else f"{relative_reduction:.1%}"
    markdown = f"""# Paired holdout analysis\n\nPairs: **{total}**\n\n| Metric | Baseline | Agent Flight Recorder |\n| --- | ---: | ---: |\n| Attack success | {baseline_attack}/{total} ({baseline_rate:.1%}) | {recorder_attack}/{total} ({recorder_rate:.1%}) |\n| Utility success | {baseline_utility}/{total} ({baseline_utility/total:.1%}) | {recorder_utility}/{total} ({recorder_utility/total:.1%}) |\n\nBaseline attack-success Wilson 95% CI: **{b_ci[0]:.1%} to {b_ci[1]:.1%}**.\n\nFlight Recorder attack-success Wilson 95% CI: **{r_ci[0]:.1%} to {r_ci[1]:.1%}**.\n\nAbsolute attack-risk difference (Flight Recorder - baseline): **{risk_difference:.1%}**.\n\nRelative reduction: **{rr_text}**.\n\nPaired discordance: baseline-success/Recorder-resisted = **{baseline_only}**; baseline-resisted/Recorder-success = **{recorder_only}**.\n\nExact two-sided McNemar p-value: **{p_value:.6g}**.\n\n## Interpretation boundary\n\n{result['interpretationBoundary']}\n"""
    options.markdown.write_text(markdown, encoding="utf-8")
    print(markdown)


if __name__ == "__main__":
    main()
