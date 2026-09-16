# AgentDojo integration

This adapter replaces AgentDojo's normal tool executor. Every proposed tool call is mapped by trusted catalog data, assessed by the TypeScript `FlightRecorder`, and executed only when policy permits it.

Unmapped tools fail closed. Review uses a declared scripted policy because AgentDojo is a non-interactive benchmark. Successful tool calls are recorded as causal history; blocked, denied, and failed calls are not.

Each AgentDojo benchmark query receives a fresh policy session. Tool-loop iterations within that query reuse the same session. History never crosses task boundaries.

## Setup

```powershell
npm run build
py -m venv .venv-agentdojo
.venv-agentdojo\Scripts\Activate.ps1
python -m pip install -r integrations/agentdojo/requirements.txt
python integrations/agentdojo/test_executor.py
```

Set the existing Azure OpenAI environment variables in the same PowerShell window. Then run a small workspace slice:

```powershell
python integrations/agentdojo/run_benchmark.py `
  --suite workspace `
  --user-task user_task_0 `
  --injection-task injection_task_0 `
  --attack tool_knowledge `
  --force-rerun
```

Run the same slice without the gate:

```powershell
python integrations/agentdojo/run_benchmark.py `
  --mode baseline `
  --suite workspace `
  --user-task user_task_0 `
  --injection-task injection_task_0 `
  --attack tool_knowledge `
  --force-rerun
```

Use identical task, injection, attack, model, and benchmark versions for both modes. Keep `--review-policy approve` for the primary comparison. A separate `deny` run measures the security and utility cost of rejecting every Review decision.

The checked-in catalog exactly covers the 24 tools in AgentDojo 0.1.35's `v1.2.2` workspace suite. A test detects catalog drift. Other suites remain unsupported, and the adapter blocks their unmapped tools.

## Research limits

The catalog is hand-authored trusted metadata. AgentDojo does not supply sensitivity labels or artifact lineage. This integration measures runtime interception and session-history policy. It does not yet evaluate artifact-aware attribution. Results must state that scope and report the pinned AgentDojo version.
# AgentDojo integration

Outbound email trust is configured at runtime, never inferred from model output. Pass one or more trusted tenant domains when running a benchmark:

```bash
python integrations/agentdojo/run_benchmark.py --trusted-email-domain bluesparrowtech.com ...
```

Recipients outside those domains are labeled `Untrusted` before the TypeScript policy engine decides whether the tool call may execute.
