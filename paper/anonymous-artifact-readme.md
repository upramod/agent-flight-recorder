# Anonymous artifact preparation guide

Target: USENIX Security 2027 Cycle 2.

This file is a staging guide for the anonymous review artifact. Do not upload the live development repository directly. Its owner name, commit history, Actions metadata, and prior author-facing files can identify the authors.

## Reviewer package contents

The anonymous package should contain:

- `src/` deterministic policy engine, gate, lineage logic, and policy bridge;
- `test/` automated policy and execution-semantics tests;
- `integrations/agentdojo/` adapter, trusted tool catalog, benchmark runners, analyzers, protocol tests, and frozen manifests needed for the reported study;
- `package.json`, `package-lock.json`, and `tsconfig.json`;
- sanitized reproduction instructions;
- frozen v2 `manifest-v2.generated.json`;
- frozen v2 `manifest-v2.runner.json`;
- frozen `summary.csv`;
- frozen `analysis.json` and `analysis.md`;
- SHA-256 records for the supplied evidence files.

Do not include `.git/`, author profiles, repository-owner URLs, private CI secrets, personal contact information, unpublished immigration material, or any file whose sole purpose is authorship or project history.

## Reproduction levels

### Level 1: deterministic local verification

Reviewers can run:

```bash
npm ci
npm test
python -m pip install -r integrations/agentdojo/requirements.txt
python integrations/agentdojo/test_executor.py
python integrations/agentdojo/test_v2_protocol.py
```

These checks verify policy semantics, adapter behavior, deterministic v2 selection, pair uniqueness, and overlap exclusion. They do not require model credentials.

### Level 2: frozen-result verification

Reviewers can inspect the supplied v2 manifest and `summary.csv`, then rerun the paired analysis script:

```bash
python integrations/agentdojo/analyze_paired.py \
  evidence/summary.csv \
  --json reproduced-analysis.json \
  --markdown reproduced-analysis.md
```

Expected primary result:

- baseline attack success: 20/120;
- Recorder attack success: 0/120;
- exact two-sided McNemar p-value: 1.90735e-06.

The paired utility analysis should recover 61/120 baseline success, 35/120 Recorder success, 29 baseline-success/Recorder-failure pairs, 3 opposite-direction pairs, and exact two-sided McNemar p=2.55601e-06.

### Level 3: live model reproduction

A full rerun requires a compatible Azure OpenAI deployment and credentials. Credentials cannot be distributed. The artifact should document the required environment variable names but must not contain values.

Required variables:

```text
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_DEPLOYMENT
AZURE_OPENAI_API_KEY
AZURE_OPENAI_API_VERSION
```

Model nondeterminism means a fresh live rerun is not expected to reproduce every per-case trajectory exactly. The frozen raw and aggregate evidence is supplied so reviewers can verify the reported experiment separately from any fresh stochastic rerun.

## Anonymity checks before upload

Search every text file in the staged bundle for:

```text
Pramod
Ubbala
upramod
microsoft.com
Microsoft
linkedin.com
github.com/upramod
```

Any match must be reviewed. Remove identifying metadata that is not required to reproduce the research.

Inspect ZIP metadata, PDF metadata, README links, workflow badges, package metadata, and source comments. The anonymous hosting URL must not reveal the authors and must not track reviewer access.

## Evidence integrity

The successful v2 workflow artifact has SHA-256:

`3a4e8c97a8237b8f2fa5eae08f9fc2e4188c72173ff594a58680b7b907faac81`

The generated v2 manifest has SHA-256:

`133014deda3d84607e29270525fce26e45b3f75b2b4f94559135c373f4b1b3aa`

Keep the original downloaded workflow artifact outside the anonymous mirror as the archival source. Build the reviewer bundle from explicit allowlists rather than deleting files from a full clone.
