# Artifact provenance

Trusted adapters assign dataFlow.inputs and dataFlow.outputs. These identifiers are session-local, immutable references to synthetic data. Model proposals cannot set them.

The recorder resolves input ancestry using only successfully recorded producers. Derived artifacts inherit the strongest source sensitivity and untrusted provenance. Assessing an action with dataFlow never records it; ExecutionGate records after its synchronous executor succeeds.

Unknown inputs, cross-session references, reused output IDs and uploads without inputs are blocked. Explicitly linked public exports do not inherit unrelated restricted-data history. Sensitive artifacts sent outside the trusted boundary are blocked even if the current action labels them Public.

Run npm test and then npm start. Select Artifact provenance in Scripted replay. The fifth action uploads the public export (Allow); the sixth attempts the restricted export (Block). Both exports exist in the same session. This is an offline deterministic test, not a live-model attack.

Live Azure adapters now attach document → records → export links. The live dashboard displays inputs, outputs and effective sensitivity.

Legacy actions without dataFlow retain the original session-wide heuristic rules for compatibility. New integrations must supply complete trusted dependencies; this prototype does not discover omitted dependencies, inspect arbitrary file bytes or authenticate external tool adapters. The existing gate supports synchronous synthetic executors only.

A fresh recorder cannot resolve artifact references and blocks them. Do not claim an Allow-versus-Block improvement against that fail-closed baseline. This feature demonstrates correct data attribution and fewer unrelated history effects, not unique security capability.
