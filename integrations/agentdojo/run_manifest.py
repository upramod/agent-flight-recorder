from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from agentdojo.task_suite.load_suites import get_suite


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    options = args()
    manifest = json.loads(options.manifest.read_text(encoding="utf-8"))
    suite_name = manifest["suite"]
    version = manifest["benchmarkVersion"]
    suite = get_suite(version, suite_name)
    valid_users = set(suite.user_tasks)
    valid_injections = set(suite.injection_tasks)
    pairs = manifest["pairs"]
    if not pairs:
        raise ValueError("Benchmark manifest must contain at least one pair")
    seen: set[tuple[str, str]] = set()
    for pair in pairs:
        key = (pair["userTask"], pair["injectionTask"])
        if key in seen:
            raise ValueError(f"Duplicate benchmark pair: {key}")
        seen.add(key)
        if key[0] not in valid_users:
            raise ValueError(f"Unknown user task for {version}/{suite_name}: {key[0]}")
        if key[1] not in valid_injections:
            raise ValueError(f"Unknown injection task for {version}/{suite_name}: {key[1]}")

    options.output.mkdir(parents=True, exist_ok=True)
    metadata = {
        "manifest": manifest,
        "pairCount": len(pairs),
        "agentdojoUserTaskCount": len(valid_users),
        "agentdojoInjectionTaskCount": len(valid_injections),
        "azureDeployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
        "gitSha": os.getenv("GITHUB_SHA", ""),
        "githubRunId": os.getenv("GITHUB_RUN_ID", ""),
    }
    (options.output / "run-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    runner = Path(__file__).with_name("run_benchmark.py")
    for index, pair in enumerate(pairs):
        case = options.output / f"case-{index:02d}"
        for mode in ("baseline", "flight-recorder"):
            logdir = case / mode
            logdir.mkdir(parents=True, exist_ok=True)
            command = [
                sys.executable, str(runner),
                "--mode", mode,
                "--suite", suite_name,
                "--benchmark-version", version,
                "--user-task", pair["userTask"],
                "--injection-task", pair["injectionTask"],
                "--attack", manifest["attack"],
                "--trusted-email-domain", manifest["trustedEmailDomain"],
                "--logdir", str(logdir),
                "--force-rerun",
            ]
            if mode == "flight-recorder":
                command.extend(["--review-policy", manifest["reviewPolicy"]])
            completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            console = case / f"{mode}-console.txt"
            console.write_text(completed.stdout, encoding="utf-8")
            print(f"[{pair['id']}] {mode}\n{completed.stdout}", flush=True)
            if completed.returncode != 0:
                raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
