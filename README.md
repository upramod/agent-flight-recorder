# Agent Flight Recorder

Runtime security for tool-using AI agents.

Agent Flight Recorder evaluates observable runtime behavior before a tool action executes. It does not read, store, or expose private chain-of-thought. It receives structured action metadata, keeps a session history, calculates trajectory risk, and returns one of three policy decisions:

- **Allow**: low-risk action.
- **Review**: a human or higher-trust control should inspect the action.
- **Block**: the action must not execute.

## First demo

The demo models this sequence:

```
untrusted document
  -> restricted records query
  -> restricted export
  -> external connection
  -> external upload
```

Each action can look reasonable in isolation. The final upload is dangerous because the recorder sees the sequence, not just the last API call. The deterministic policy blocks it before execution.

## Run it

Requires Node.js 20 or later.

```bash
npm install
npm run demo
npm test
```

## Design

The prototype uses five layers:

1. **Action schema**. Captures tool, operation, resource, sensitivity, destination trust, privilege, provenance, session, and time.
2. **Flight recorder**. Stores observable events by session.
3. **Risk model**. Adds transparent points for risky metadata and action combinations.
4. **Policy engine**. Maps scores to Allow, Review, or Block.
5. **Execution gate**. The caller must assess the action before invoking the real tool.

The risk score is a demo model, not a security guarantee. Production use requires threat modeling, policy review, access control, logging safeguards, and evaluation against representative workloads.

## Boundaries

This project does not infer private reasoning. It does not claim that a risky intent exists inside an agent. It evaluates the action trajectory visible at the tool boundary.

All demo data and destinations are synthetic. The project contains no confidential workplace information.

## Future evaluation

Once the prototype works, we can compare point-action monitoring with trajectory-aware monitoring using detection rate, false-positive rate, time-to-detection, and enforcement overhead. We will review existing research before making novelty claims.
