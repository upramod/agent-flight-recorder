# Agent Flight Recorder

Runtime security for tool-using AI agents.

Agent Flight Recorder evaluates observable runtime behavior before a tool action executes. It does not read, store, or expose private chain-of-thought. It receives structured action metadata, keeps a session history, calculates trajectory risk, and returns one of three policy decisions:

- **Allow**. Low-risk action may execute.
- **Review**. Approval is required before execution.
- **Block**. The action must not execute.

## Demo

The main scenario models a multi-step data-exfiltration attempt:

```
untrusted document
  -> restricted records query
  -> restricted export
  -> external connection
  -> external upload
```

The first four actions are approved in the demo. The final upload is blocked by the execution gate.

The dashboard also includes safe and suspicious scenarios. Select a scenario to compare point-action monitoring with trajectory-aware monitoring.

## Run locally

Requires Node.js 20 or later.

```bash
npm install
npm test
npm run demo
npm start
```

Open [http://localhost:3000](http://localhost:3000) after `npm start`.

## Architecture

```
Agent proposes an action
        |
        v
Structured action metadata
        |
        v
FlightRecorder assesses current action + executed session history
        |
        v
ExecutionGate returns Allow, Review, or Block
        |
        +--> Allow or approved Review: execute and record
        +--> Block or unapproved Review: do not execute
        |
        v
Dashboard displays the trajectory and decision reasons
```

### Core files

- `src/types.ts`. Observable action and assessment types.
- `src/engine.ts`. Transparent trajectory risk model and policy thresholds.
- `src/gate.ts`. Execution enforcement and executed-history handling.
- `src/scenario.ts`. Synthetic safe, suspicious, and exfiltration scenarios.
- `src/server.ts`. Local API and dashboard server.
- `dashboard/`. Browser dashboard.
- `test/engine.test.mjs`. Policy and gate tests.

## Risk model

The prototype uses transparent points:

- Untrusted document input: +20
- Confidential data: +15
- Restricted data: +25
- Unknown destination: +15
- Untrusted destination: +30
- High privilege: +15
- Untrusted input followed by sensitive access: +20
- Sensitive export uploaded after sensitive access: +30
- Export crossing the trusted boundary: +20

Thresholds:

```
0-39    Allow
40-69   Review
70-100  Block
```

This is a demonstration model, not a production security guarantee. Production deployment requires threat modeling, policy review, access control, privacy controls, and evaluation against representative workloads.

## Azure OpenAI integration boundary

The planned Azure version will use Azure OpenAI to help an agent interpret synthetic documents and propose structured tool actions. Every proposal will pass through the same deterministic FlightRecorder and ExecutionGate.

```
Azure OpenAI agent
        -> proposes action
Flight Recorder
        -> evaluates trajectory
Deterministic policy engine
        -> enforces decision
Tool adapter
        -> executes only when permitted
```

Azure OpenAI will not make the final allow or block decision. No confidential workplace data is required. The planned cloud demo will use synthetic documents, fake records, and a fake external destination.

## Scope boundary

This project evaluates observable runtime behavior at the tool boundary. It does not infer private reasoning or claim that a hidden intent exists inside an agent.

Future experiments may compare point-action monitoring with trajectory-aware monitoring using detection rate, false-positive rate, time-to-detection, and enforcement overhead. We will review existing research before making novelty claims.
