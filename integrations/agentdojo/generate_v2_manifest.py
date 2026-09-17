#!/usr/bin/env python3
"""Generate protocol-v2 eligibility inventory and manifest without model calls.

The generator deliberately does not read result/evidence files. Prior evaluated
identities are excluded from the frozen diagnostic and holdout manifests.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIOR = [HERE / "benchmark-manifest.json", HERE / "holdout-manifest.json"]
TARGET = 120


def load(path):
    return json.loads(path.read_text())


def cases(doc):
    if isinstance(doc, list): return doc
    for key in ("cases", "pairs", "items", "manifest"):
        if isinstance(doc.get(key), list): return doc[key]
    raise ValueError("manifest has no case list")


def ident(c):
    u = c.get("user_task_id", c.get("userTaskId", c.get("user_task", c.get("userTask"))))
    i = c.get("injection_task_id", c.get("injectionTaskId", c.get("injection_task", c.get("injectionTask"))))
    if u is None or i is None:
        raise ValueError(f"missing task id: {c}")
    return str(u), str(i)


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def key(s): return hashlib.sha256(("afr-v2|" + s).encode()).hexdigest()


def main(out_path):
    used = set()
    prior_hashes = {}
    for p in PRIOR:
        prior_hashes[p.name] = digest(p)
        used.update(ident(c) for c in cases(load(p)))

    universe = [(f"user_task_{u}", f"injection_task_{i}") for u in range(40) for i in range(14)]
    eligible = [x for x in universe if x not in used]
    ranked = sorted(eligible, key=lambda x: key("|".join(x)))
    selected = ranked[:TARGET]
    if len(selected) < TARGET:
        print(f"eligible universe shortfall: {len(selected)} < {TARGET}", file=sys.stderr)

    doc = {
        "protocol": "paper/independent-evaluation-protocol-v2.md",
        "status": "frozen-before-model-calls",
        "agentdojo_benchmark": "v1.2.2",
        "suite": "workspace",
        "attack": "tool_knowledge",
        "review_policy": "deny",
        "trusted_domain": "bluesparrowtech.com",
        "selection": "sha256('afr-v2|user_task_id|injection_task_id') ascending",
        "target": TARGET,
        "eligible_count": len(eligible),
        "prior_manifest_sha256": prior_hashes,
        "cases": [
            {"user_task_id": u, "injection_task_id": i, "selection_key": key(f"{u}|{i}")}
            for u, i in selected
        ],
    }
    Path(out_path).write_text(json.dumps(doc, indent=2) + "\n")
    print(f"selected {len(selected)} unique pairs from {len(eligible)} eligible")

if __name__ == "__main__":
    if len(sys.argv) != 2: raise SystemExit("usage: generate_v2_manifest.py OUTPUT")
    main(sys.argv[1])
