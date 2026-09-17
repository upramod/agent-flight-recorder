from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


ORDERS = [
    ("baseline", "deny", "approve"),
    ("deny", "approve", "baseline"),
    ("approve", "baseline", "deny"),
    ("baseline", "approve", "deny"),
    ("deny", "baseline", "approve"),
]


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: run_repeated_trials.py MANIFEST OUTPUT_ROOT")
    manifest_path = Path(sys.argv[1])
    root = Path(sys.argv[2])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    runner = Path(__file__).with_name("run_benchmark.py")
    root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []

    for block_index, order in enumerate(ORDERS, start=1):
        for condition in order:
            for case_index, pair in enumerate(manifest["pairs"]):
                mode = "baseline" if condition == "baseline" else "flight-recorder"
                review = "approve" if condition == "approve" else "deny"
                logdir = root / f"block-{block_index:02d}" / condition / f"case-{case_index:02d}"
                logdir.mkdir(parents=True, exist_ok=True)
                command = [
                    sys.executable, str(runner),
                    "--mode", mode,
                    "--suite", manifest["suite"],
                    "--benchmark-version", manifest["benchmarkVersion"],
                    "--user-task", pair["userTask"],
                    "--injection-task", pair["injectionTask"],
                    "--attack", manifest["attack"],
                    "--trusted-email-domain", manifest["trustedEmailDomain"],
                    "--logdir", str(logdir),
                    "--force-rerun",
                ]
                if mode == "flight-recorder":
                    command.extend(["--review-policy", review])
                completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                console = logdir / "console.txt"
                console.write_text(completed.stdout, encoding="utf-8")
                print(f"block={block_index} condition={condition} pair={pair['id']}\n{completed.stdout}", flush=True)
                if completed.returncode != 0:
                    raise SystemExit(completed.returncode)
                values = {}
                for line in completed.stdout.splitlines():
                    for key in ("utility", "attack_success", "attack_resisted"):
                        if line.startswith(key + "="):
                            passed, total = line.split("=", 1)[1].split("/", 1)
                            values[key] = (int(passed), int(total))
                if set(values) != {"utility", "attack_success", "attack_resisted"}:
                    raise ValueError(f"Incomplete output for block {block_index} {condition} {pair['id']}")
                rows.append({
                    "block": block_index,
                    "condition": condition,
                    "case": pair["id"],
                    "user_task": pair["userTask"],
                    "injection_task": pair["injectionTask"],
                    "utility": values["utility"][0],
                    "attack_success": values["attack_success"][0],
                    "attack_resisted": values["attack_resisted"][0],
                })

    output = root / "repeated-trials.csv"
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "orders": ORDERS,
        "blocks": len(ORDERS),
        "pairsPerConditionPerBlock": len(manifest["pairs"]),
        "gitSha": os.getenv("GITHUB_SHA", ""),
        "githubRunId": os.getenv("GITHUB_RUN_ID", ""),
        "azureDeployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
        "manifest": manifest,
    }
    (root / "repeated-trials-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
