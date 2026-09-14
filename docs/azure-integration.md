# Azure proposal adapter

Status: integration seam and one-proposal CLI smoke test. Not a complete agent loop or dashboard integration.

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
Add a bounded model/tool loop, real synthetic tool outputs, explicit approval controls and artifact-level provenance. Preserve the deterministic dashboard as a clearly labeled replay mode.
