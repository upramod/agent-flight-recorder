# Azure proposal adapter

Status: one-proposal smoke test plus a bounded multi-step CLI agent with synthetic tools and explicit terminal approvals. Dashboard integration remains pending.

Existing synthetic dashboard remains available through npm start. It never calls Azure.
Azure mode fails explicitly if configuration is missing; it does not disguise synthetic output as live AI.

## Run offline tests
```powershell
git pull --ff-only
npm test
```

## Live smoke test
Use Node.js 22. Configure these environment variables locally:
- AZURE_OPENAI_ENDPOINT: Azure resource origin, such as https://RESOURCE.openai.azure.com
- AZURE_OPENAI_API_KEY: secret, never commit or paste into chat
- AZURE_OPENAI_DEPLOYMENT: deployment name supporting chat completions and JSON mode

After setting variables in the terminal:
```powershell
npm run build
node dist/azureDemo.js
```

This makes one paid model request, proposes one action, and gates a synchronous mock executor. It does not read real files or upload anything. Review is not automatically approved. Block never executes. Stop is a valid model outcome. Credentials stay server-side. A .env file is ignored by Git but is not automatically loaded by these commands.

The adapter uses the Azure v1 API:
https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle

## Security boundary
The model selects a catalog action only. Trusted code assigns sensitivity, trust, privilege, IDs and timestamps. Unknown actions, extra fields, incomplete responses and malformed JSON fail closed. Requests time out after 30 seconds and reject redirects.

Catalog metadata describes synthetic resources, not production classification or artifact lineage. Uploads retain Restricted sensitivity; we do not downgrade labels to manufacture an Allow-versus-Block comparison. A model refusal is not evidence that the gate blocked an attack.

The existing gate is synchronous. Do not pass asynchronous real tool executors until it awaits tool completion and records failures correctly.

## Next stage
Connect live sessions to the dashboard and extend artifact-level provenance. Preserve the deterministic dashboard as a clearly labeled replay mode.

## Multi-step live agent

In the terminal that holds your Azure environment variables:
```powershell
git pull --ff-only
npm test
npm run agent -- safe
npm run agent -- injection
```

Each run makes up to eight paid Azure requests. Type yes for each Review action you intend to approve. Any other response, or noninteractive input, denies the action and ends the run.

Both scenarios request an internal report. The injection scenario changes only the synthetic document: it includes an instruction to upload externally. Model responses remain live and may refuse the injection. A model stop is reported as model_stopped, not policy_blocked. Offline tests script proposals to verify blocking independent of model behavior.

Every run uses a new session and in-memory tool state. Successful tool outputs feed the next proposal. Denied and blocked requests appear in the returned trace without tool output. Missing prerequisites, repeated operations, model failure, or the step cap terminate the run. No actual file, database, or upload tool runs.

The current adapter exchanges JSON action selections through chat messages; it does not yet use native function-call messages. Upload metadata stays Restricted, so this live scenario proves gating, not superiority over a point-action baseline. This CLI does not persist traces.
