from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path


RESULT = re.compile(r"^(utility|security)=(\d+)/(\d+)$", re.MULTILINE)


def parse_console(path: Path) -> dict[str, tuple[int, int]]:
    values = {name: (int(passed), int(total)) for name, passed, total in RESULT.findall(path.read_text())}
    if set(values) != {"utility", "security"}:
        raise ValueError(f"Incomplete benchmark output: {path}")
    return values


def summarize(root: Path) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for path in sorted(root.glob("case-*/**/*-console.txt")):
        case = path.relative_to(root).parts[0]
        mode = path.stem.removesuffix("-console")
        values = parse_console(path)
        policy = {"allow": "", "review": "", "block": "", "executed": "", "denied": ""}
        audit_path = path.parent / mode / "flight-recorder-policy.jsonl"
        if audit_path.exists():
            events = [json.loads(line) for line in audit_path.read_text().splitlines() if line]
            decisions = [event.get("assessment", {}).get("decision", event.get("decision")) for event in events]
            policy = {
                "allow": decisions.count("Allow"),
                "review": decisions.count("Review"),
                "block": decisions.count("Block"),
                "executed": sum(bool(event.get("executed")) for event in events),
                "denied": sum(not bool(event.get("executed")) for event in events),
            }
        rows.append({
            "case": case,
            "mode": mode,
            "utility_passed": values["utility"][0],
            "utility_total": values["utility"][1],
            "security_passed": values["security"][0],
            "security_total": values["security"][1],
            **policy,
        })
    if not rows:
        raise ValueError(f"No pilot console files found under {root}")
    return rows


def write_summary(rows: list[dict[str, str | int]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    for mode in ("baseline", "flight-recorder"):
        selected = [row for row in rows if row["mode"] == mode]
        utility = sum(int(row["utility_passed"]) for row in selected)
        utility_total = sum(int(row["utility_total"]) for row in selected)
        security = sum(int(row["security_passed"]) for row in selected)
        security_total = sum(int(row["security_total"]) for row in selected)
        print(f"{mode}: utility={utility}/{utility_total} security={security}/{security_total}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: summarize_pilot.py RESULTS_ROOT OUTPUT_CSV")
    write_summary(summarize(Path(sys.argv[1])), Path(sys.argv[2]))
