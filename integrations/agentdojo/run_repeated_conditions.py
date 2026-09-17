from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from agentdojo.task_suite.load_suites import get_suite


RESULT = re.compile(r"^(utility|attack_success|attack_resisted)=(\d+)/(\d+)$", re.MULTILINE)

CONDITIONS = {
    "baseline": {"mode": "baseline", "review_policy": "approve"},
    "flight-recorder-deny": {"mode": "flight-recorder", "review_policy": "deny"},
    "flight-recorder-approve": {"mode": "flight-recorder", "review_policy": "approve"},
}

ORDERS = {
    1: ["baseline", "flight-recorder-deny", "flight-recorder-approve"],
    2: ["flight-recorder-deny", "flight-recorder-approve", "baseline"],
    3: ["flight-recorder-approve", "baseline", "flight-recorder-deny"],
    4: ["baseline", "flight-recorder-approve", "flight-recorder-deny"],
    5: ["flight-recorder-deny", "baseline", "flight-recorder-approve"],
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--exclude-manifest", type=Path, required=True)
    parser.add_argument("--repeat", type=int, choices=range(1, 6), required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def read_manifest(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def parse_console(text: str) -> dict[str, int]:
    values = {name: (int(passed), int(total)) for name, passed, total in RESULT.findall(text)}
    required = {"utility", "attack_success", "attack_resisted"}
    if set(values) != required:
        raise ValueError("Incomplete benchmark output")
    return {
        "utility_passed": values["utility"][0],
        "utility_total": values["utility"][1],
        "attack_success": values["attack_success"][0],
        "attack_total": values["attack_success"][1],
        "attack_resisted": values["attack_resisted"][0],
    }


def main() -> None:
    options = arguments()
    manifest, manifest_sha = read_manifest(options.manifest)
    excluded, excluded_sha = read_manifest(options.exclude_manifest)

    if manifest["benchmarkVersion"] != excluded["benchmarkVersion"] or manifest["suite"] != excluded["suite"]:
        raise ValueError("Manifest and excluded manifest must use the same benchmark version and suite")

    suite = get_suite(manifest["benchmarkVersion"], manifest["suite"])
    valid_users = set(suite.user_tasks)
    valid_injections = set(suite.injection_tasks)

    pairs = manifest["pairs"]
    if len(pairs) != 30:
        raise ValueError(f"Repeated study requires exactly 30 pairs, got {len(pairs)}")

    seen: set[tuple[str, str]] = set()
    for pair in pairs:
        key = (pair["userTask"], pair["injectionTask"])
        if key in seen:
            raise ValueError(f"Duplicate pair: {key}")
        seen.add(key)
        if key[0] not in valid_users:
            raise ValueError(f"Unknown user task: {key[0]}")
        if key[1] not in valid_injections:
            raise ValueError(f"Unknown injection task: {key[1]}")

    excluded_pairs = {(p["userTask"], p["injectionTask"]) for p in excluded["pairs"]}
    overlap = seen & excluded_pairs
    if overlap:
        raise ValueError(f"Repeated-study manifest overlaps excluded diagnostic pairs: {sorted(overlap)}")

    order = ORDERS[options.repeat]
    output = options.output
    output.mkdir(parents=True, exist_ok=True)

    metadata = {
        "repeat": options.repeat,
        "conditionOrder": order,
        "manifestPath": str(options.manifest),
        "manifestSha256": manifest_sha,
        "excludeManifestPath": str(options.exclude_manifest),
        "excludeManifestSha256": excluded_sha,
        "benchmarkVersion": manifest["benchmarkVersion"],
        "suite": manifest["suite"],
        "attack": manifest["attack"],
        "trustedEmailDomain": manifest["trustedEmailDomain"],
        "pairCount": len(pairs),
        "azureDeployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
        "gitSha": os.getenv("GITHUB_SHA", ""),
        "githubRunId": os.getenv("GITHUB_RUN_ID", ""),
    }
    (output / "run-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    runner = Path(__file__).with_name("run_benchmark.py")
    rows: list[dict[str, str | int]] = []

    for index, pair in enumerate(pairs):
        case_dir = output / f"case-{index:02d}"
        case_dir.mkdir(parents=True, exist_ok=True)
        for condition in order:
            config = CONDITIONS[condition]
            logdir = case_dir / condition
            logdir.mkdir(parents=True, exist_ok=True)
            command = [
                sys.executable,
                str(runner),
                "--mode",
                config["mode"],
                "--suite",
                manifest["suite"],
                "--benchmark-version",
                manifest["benchmarkVersion"],
                "--user-task",
                pair["userTask"],
                "--injection-task",
                pair["injectionTask"],
                "--attack",
                manifest["attack"],
                "--trusted-email-domain",
                manifest["trustedEmailDomain"],
                "--logdir",
                str(logdir),
                "--force-rerun",
            ]
            if config["mode"] == "flight-recorder":
                command.extend(["--review-policy", config["review_policy"]])

            completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            console_path = case_dir / f"{condition}-console.txt"
            console_path.write_text(completed.stdout, encoding="utf-8")
            print(f"[repeat-{options.repeat} {pair['id']} {condition}]\n{completed.stdout}", flush=True)
            if completed.returncode != 0:
                raise SystemExit(completed.returncode)

            result = parse_console(completed.stdout)
            rows.append(
                {
                    "repeat": options.repeat,
                    "case": f"case-{index:02d}",
                    "pair_id": pair["id"],
                    "user_task": pair["userTask"],
                    "injection_task": pair["injectionTask"],
                    "condition": condition,
                    **result,
                }
            )

    summary_csv = output / "repeat-results.csv"
    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    aggregates: dict[str, dict[str, int | float]] = {}
    for condition in CONDITIONS:
        selected = [row for row in rows if row["condition"] == condition]
        utility = sum(int(row["utility_passed"]) for row in selected)
        utility_total = sum(int(row["utility_total"]) for row in selected)
        attacks = sum(int(row["attack_success"]) for row in selected)
        attack_total = sum(int(row["attack_total"]) for row in selected)
        aggregates[condition] = {
            "utility": utility,
            "utilityTotal": utility_total,
            "utilityRate": utility / utility_total if utility_total else 0.0,
            "attackSuccess": attacks,
            "attackTotal": attack_total,
            "attackSuccessRate": attacks / attack_total if attack_total else 0.0,
            "attackResisted": attack_total - attacks,
        }
        print(
            f"repeat={options.repeat} condition={condition} "
            f"utility={utility}/{utility_total} attack_success={attacks}/{attack_total}"
        )

    (output / "repeat-summary.json").write_text(
        json.dumps({"repeat": options.repeat, "conditionOrder": order, "aggregates": aggregates}, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
