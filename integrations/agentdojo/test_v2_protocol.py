#!/usr/bin/env python3
import json
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GEN = HERE / "generate_v2_manifest.py"


def load(p): return json.loads(Path(p).read_text())
def cases(d):
    if isinstance(d, list): return d
    for k in ("cases", "pairs", "items", "manifest"):
        if isinstance(d.get(k), list): return d[k]
    raise AssertionError("case list missing")
def ident(c):
    return str(c.get("user_task_id", c.get("userTaskId", c.get("user_task")))), str(c.get("injection_task_id", c.get("injectionTaskId", c.get("injection_task"))))

with tempfile.TemporaryDirectory() as td:
    a, b = Path(td)/"a.json", Path(td)/"b.json"
    subprocess.run(["python", str(GEN), str(a)], check=True)
    subprocess.run(["python", str(GEN), str(b)], check=True)
    assert a.read_bytes() == b.read_bytes(), "generator must be deterministic"
    v2 = load(a)
    ids = [ident(c) for c in v2["cases"]]
    assert len(ids) == 120, len(ids)
    assert len(set(ids)) == len(ids), "v2 contains duplicates"
    used = set()
    for name in ("benchmark-manifest.json", "holdout-manifest.json"):
        used |= {ident(c) for c in cases(load(HERE/name))}
    overlap = set(ids) & used
    assert not overlap, f"prior overlap: {sorted(overlap)}"
    assert v2["review_policy"] == "deny"
print("v2 protocol tests passed")
