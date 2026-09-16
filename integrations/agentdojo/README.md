# AgentDojo integration

This adapter replaces AgentDojo's normal tool executor. Every proposed tool call is mapped by trusted catalog data, assessed by the TypeScript `FlightRecorder`, and executed only when policy permits it.

Unmapped tools fail closed. Review uses a declared scripted policy because AgentDojo is a non-interactive benchmark. Successful tool calls are recorded as causal history; blocked, denied, and failed calls are not.

## Setup

```powershell
npm run build
py -m venv .venv-agentdojo
.venv-agentdojo\Scripts\Activate.ps1
python -m pip install -r integrations/agentdojo/requirements.txt
python -m unittest integrations/agentdojo/test_executor.py
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

Do not run the full suite yet. The checked-in catalog covers only a small workspace tool subset. The adapter blocks every unmapped tool, which is safe but would invalidate utility results for tasks that require those tools.

## Research limits

The catalog is hand-authored trusted metadata. AgentDojo does not supply sensitivity labels or artifact lineage. This first integration measures runtime interception and session-history policy. It does not yet evaluate artifact-aware attribution. A publishable run requires complete, reviewed catalogs for each selected suite and a frozen AgentDojo version.
