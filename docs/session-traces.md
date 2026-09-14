# Download session traces

Both dashboards provide Download session trace.

- Scripted replay: enabled after replay completes. Downloads the displayed run without re-execution.
- Live Azure: downloads the latest successfully observed snapshot, including a pending review if present. observedAt marks when the browser received it. status distinguishes active runs, model stop, review denial and policy block.

JSON schemaVersion 1.0 includes mode, scenario, session/run IDs, action timestamps, assessments, reasons, artifact references, effective sensitivity, approval states and execution outcomes. Live synthetic tool outputs are included. Replay approvals are labeled scripted. Downloading makes no model call.

Downloads are browser-generated JSON files. They are unsigned snapshots, not tamper-evident audit logs. The existing engine does not record approval timestamps, reviewer identity or separate explicit rejection from expiry. Proposals that fail before assessment may be absent. Credentials and private reasoning are not part of the export.

After pulling this change, restart npm start in the terminal containing Azure configuration, then refresh the page. A new server process is needed to expose the live scenario name.
