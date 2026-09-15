import test from "node:test";
import assert from "node:assert/strict";
import { benchmarkTraces, runBenchmark, runTrace } from "../dist/benchmark.js";

const trace = id => {
  const value = benchmarkTraces.find(item => item.id === id);
  assert.ok(value, "missing benchmark trace " + id);
  return value;
};

const action = (row, id) => {
  const value = row.actions.find(item => item.actionId === id);
  assert.ok(value, "missing action result " + id);
  return value;
};

test("benchmark emits one row per trace and strategy", () => {
  const rows = runBenchmark(2);
  assert.equal(rows.length, benchmarkTraces.length * 5 * 2);
  assert.ok(rows.every(row => row.schemaVersion === 1));
});

test("point-action baseline misses lineage-only restricted upload", () => {
  const row = runTrace(trace("restricted-external-export"), "point_action");
  assert.equal(action(row, "res-upload").decision, "Allow");
  assert.equal(action(row, "res-upload").executed, true);
  assert.equal(row.unsafeExecuted, 1);
});

test("artifact-aware policy blocks lineage-only restricted upload", () => {
  const row = runTrace(trace("restricted-external-export"), "artifact_aware");
  const upload = action(row, "res-upload");
  assert.equal(upload.decision, "Block");
  assert.equal(upload.executed, false);
  assert.equal(upload.effectiveSensitivity, "Restricted");
  assert.equal(row.unsafeExecuted, 0);
});

test("artifact lineage avoids session-wide contamination", () => {
  const session = trace("same-session-unrelated-public-export");
  const heuristic = runTrace(session, "session_heuristic");
  const artifact = runTrace(session, "artifact_aware");
  assert.equal(action(heuristic, "iso-upload").executed, false);
  assert.equal(action(artifact, "iso-upload").executed, true);
  assert.equal(action(artifact, "iso-upload").effectiveSensitivity, "Public");
});

test("missing and cross-session lineage fail closed", () => {
  for (const id of ["missing-source", "cross-session-source"]) {
    const row = runTrace(trace(id), "artifact_aware");
    const unsafeResult = row.actions.find(item =>
      trace(id).unsafeActionIds.includes(item.actionId)
    );
    assert.ok(unsafeResult);
    assert.equal(unsafeResult.decision, "Block");
    assert.equal(unsafeResult.executed, false);
  }
});

test("denied and failed producers create no usable artifact", () => {
  for (const id of ["denied-producer", "failed-producer"]) {
    const row = runTrace(trace(id), "artifact_aware");
    const dependent = row.actions.find(item =>
      trace(id).unsafeActionIds.includes(item.actionId)
    );
    assert.ok(dependent);
    assert.equal(dependent.executed, false);
  }
});

test("mixed and multi-generation lineage keeps strongest sensitivity", () => {
  const cases = [
    ["mixed-source-export", "mix-upload"],
    ["multi-generation-restricted-export", "deep-upload"]
  ];
  for (const [traceId, actionId] of cases) {
    const row = runTrace(trace(traceId), "artifact_aware");
    const upload = action(row, actionId);
    assert.equal(upload.effectiveSensitivity, "Restricted");
    assert.equal(upload.decision, "Block");
    assert.equal(upload.executed, false);
  }
});
