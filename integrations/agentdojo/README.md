# AgentDojo integration

This adapter replaces AgentDojo's normal tool executor. Every proposed tool call is mapped by trusted catalog data, assessed by the TypeScript `FlightRecorder`, and executed only when policy permits it.

Unmapped tools fail closed. Review uses a declared scripted policy because AgentDojo is a non-interactive benchmark. Successful tool calls are recorded as causal history; blocked, denied, and failed calls are not.

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

The checked-in catalog exactly covers the 24 tools in AgentDojo 0.1.35's `v1.2.2` workspace suite. A test detects catalog drift. Other suites remain unsupported, and the adapter blocks their unmapped tools.

## Research limits

The catalog is hand-authored trusted metadata. AgentDojo does not supply sensitivity labels or artifact lineage. This integration measures runtime interception and session-history policy. It does not yet evaluate artifact-aware attribution. Results must state that scope and report the pinned AgentDojo version.
