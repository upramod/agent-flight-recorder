#!/usr/bin/env python3
"""Build a reviewer artifact from explicit allowlists.

The script never copies .git history or the paper directory. It can also import
selected frozen files from the successful v2 GitHub Actions artifact ZIP.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COPY_DIRS = [
    "src",
    "test",
    "integrations/agentdojo",
]

COPY_FILES = [
    "package.json",
    "package-lock.json",
    "tsconfig.json",
]

EVIDENCE_MEMBERS = [
    "analysis.json",
    "analysis.md",
    "manifest-v2.generated.json",
    "manifest-v2.runner.json",
    "manifest-v2.sha256",
    "summary.csv",
]

FORBIDDEN_TEXT = [
    "Pramod",
    "Ubbala",
    "upramod",
    "github.com/upramod",
    "linkedin.com",
    "microsoft.com",
]

SKIP_NAMES = {
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "results",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "anonymous-artifact")
    parser.add_argument("--evidence-zip", type=Path)
    parser.add_argument("--zip", action="store_true", dest="make_zip")
    return parser.parse_args()


def ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in SKIP_NAMES or name.endswith(".pyc")}


def copy_allowlist(destination: Path) -> None:
    for relative in COPY_DIRS:
        source = ROOT / relative
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copytree(source, destination / relative, ignore=ignore)
    for relative in COPY_FILES:
        source = ROOT / relative
        if not source.exists():
            raise FileNotFoundError(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def extract_evidence(archive: Path, destination: Path) -> None:
    evidence_dir = destination / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
        missing = [name for name in EVIDENCE_MEMBERS if name not in names]
        if missing:
            raise ValueError(f"evidence ZIP missing required files: {missing}")
        for member in EVIDENCE_MEMBERS:
            data = zf.read(member)
            (evidence_dir / Path(member).name).write_bytes(data)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_readme(destination: Path, has_evidence: bool) -> None:
    text = """# Agent Flight Recorder anonymous artifact

This package supports anonymous review of a tool-boundary runtime enforcement system for tool-using AI agents.

## Local verification

```bash
npm ci
npm test
python -m pip install -r integrations/agentdojo/requirements.txt
python integrations/agentdojo/test_executor.py
python integrations/agentdojo/test_v2_protocol.py
```

The deterministic tests require no model credentials.

## Live benchmark configuration

A full AgentDojo rerun requires a compatible Azure OpenAI deployment and these environment variables:

```text
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_DEPLOYMENT
AZURE_OPENAI_API_KEY
AZURE_OPENAI_API_VERSION
```

No credential values are included in this artifact.
"""
    if has_evidence:
        text += """
## Frozen v2 evidence

The `evidence/` directory contains the frozen manifest, paired summary, and analysis from the reported 120-pair experiment. To regenerate the primary paired analysis:

```bash
python integrations/agentdojo/analyze_paired.py \
  evidence/summary.csv \
  --json reproduced-analysis.json \
  --markdown reproduced-analysis.md
```

Expected attack result: baseline 20/120, Recorder 0/120, exact two-sided McNemar p=1.90735e-06.
"""
    (destination / "README.md").write_text(text, encoding="utf-8")


def write_checksums(destination: Path) -> None:
    rows = []
    for path in sorted(p for p in destination.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"):
        rows.append(f"{sha256(path)}  {path.relative_to(destination).as_posix()}")
    (destination / "SHA256SUMS.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def scan_identity(destination: Path) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for path in sorted(p for p in destination.rglob("*") if p.is_file()):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for needle in FORBIDDEN_TEXT:
            if needle.lower() in text.lower():
                hits.append({"file": path.relative_to(destination).as_posix(), "term": needle})
    return hits


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    copy_allowlist(output)
    has_evidence = args.evidence_zip is not None
    if args.evidence_zip is not None:
        if not args.evidence_zip.exists():
            raise FileNotFoundError(args.evidence_zip)
        extract_evidence(args.evidence_zip, output)

    write_readme(output, has_evidence)
    write_checksums(output)

    hits = scan_identity(output)
    (output / "anonymity-scan.json").write_text(json.dumps(hits, indent=2) + "\n", encoding="utf-8")
    if hits:
        print("Identity scan failed:", file=sys.stderr)
        for hit in hits:
            print(f"  {hit['file']}: {hit['term']}", file=sys.stderr)
        raise SystemExit(2)

    if args.make_zip:
        archive_base = output.parent / output.name
        archive = shutil.make_archive(str(archive_base), "zip", root_dir=output)
        print(f"wrote {archive}")
    else:
        print(f"wrote {output}")


if __name__ == "__main__":
    main()
