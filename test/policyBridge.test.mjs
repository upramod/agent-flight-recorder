import test from "node:test";
import assert from "node:assert/strict";
import { FlightRecorder } from "../dist/engine.js";
import { handleBridgeRequest } from "../dist/policyBridge.js";

const action = (id, operation, extra = {}) => ({
  id,
  sessionId: "agentdojo-test",
  timestamp: new Date().toISOString(),
  tool: "workspace",
  operation,
  resourceType: "document",
  sensitivity: "Internal",
  destinationTrust: "Trusted",
  privilegeLevel: 1,
  inputProvenance: "External",
  ...extra
});

test("bridge assessment does not mutate executed history", () => {
  const recorder = new FlightRecorder();
  const first = action("a1", "search_files");
  const response = handleBridgeRequest(recorder, { command: "assess", action: first });
  assert.equal(response.assessment.historyLength, 0);
  assert.equal(recorder.history(first.sessionId).length, 0);
});

test("bridge records only an explicit successful execution", () => {
  const recorder = new FlightRecorder();
  const first = action("a1", "search_files");
  handleBridgeRequest(recorder, { command: "record", action: first });
  const history = handleBridgeRequest(recorder, { command: "history", sessionId: first.sessionId });
  assert.equal(history.history.length, 1);
  assert.equal(history.history[0].id, "a1");
});

test("bridge fails closed on unresolved AgentDojo lineage", () => {
  const recorder = new FlightRecorder();
  const upload = action("a2", "share_file", {
    destinationTrust: "Untrusted",
    dataFlow: { inputs: ["missing-file"], outputs: [] }
  });
  const response = handleBridgeRequest(recorder, { command: "assess", action: upload });
  assert.equal(response.assessment.decision, "Block");
  assert.equal(recorder.history(upload.sessionId).length, 0);
});

test("point-only removes the external-calendar history rule but retains audit records", () => {
  const recorder = new FlightRecorder();
  const read = action("calendar-read", "search_calendar_events", {
    resourceType: "calendar_event"
  });
  handleBridgeRequest(recorder, { command: "record", action: read });
  const write = action("calendar-write", "create_calendar_event", {
    resourceType: "calendar_event",
    inputProvenance: "User",
    destinationTrust: "Untrusted"
  });
  const full = handleBridgeRequest(recorder, {
    command: "assess", action: write, policyMode: "full-history"
  }).assessment;
  const point = handleBridgeRequest(recorder, {
    command: "assess", action: write, policyMode: "point-only"
  }).assessment;
  assert.equal(full.score, 40);
  assert.equal(full.decision, "Review");
  assert.equal(full.historyLength, 1);
  assert.equal(point.score, 30);
  assert.equal(point.decision, "Allow");
  assert.equal(point.historyLength, 0);

  handleBridgeRequest(recorder, { command: "record", action: write });
  const again = handleBridgeRequest(recorder, {
    command: "assess", action: write, policyMode: "point-only"
  }).assessment;
  assert.deepEqual(again, point);
  assert.deepEqual(recorder.history(write.sessionId).map(event => event.id), [read.id, write.id]);
});

test("omitting policyMode preserves full-history assessment", () => {
  const recorder = new FlightRecorder();
  recorder.record(action("external-read", "search_files"));
  const query = action("sensitive-read", "get_file_by_id", {
    sensitivity: "Confidential", inputProvenance: "User"
  });
  const implicit = handleBridgeRequest(recorder, { command: "assess", action: query });
  const explicit = handleBridgeRequest(recorder, {
    command: "assess", action: query, policyMode: "full-history"
  });
  assert.deepEqual(implicit, explicit);
  assert.equal(implicit.assessment.score, 35);
  assert.equal(implicit.assessment.historyLength, 1);
});

test("point-only keeps the engine's point weights and decision thresholds", () => {
  const recorder = new FlightRecorder();
  recorder.record(action("external-read", "create_export", { sensitivity: "Restricted" }));
  const cases = [
    [{ inputProvenance: "User" }, 0, "Allow"],
    [{ sensitivity: "Confidential" }, 35, "Allow"],
    [{ inputProvenance: "User", sensitivity: "Restricted", privilegeLevel: 4 }, 40, "Review"],
    [{ inputProvenance: "User", sensitivity: "Restricted", privilegeLevel: 4,
      destinationTrust: "Untrusted" }, 70, "Block"]
  ];
  for (const [fields, score, decision] of cases) {
    const proposal = action(`score-${score}`, "upload", fields);
    const point = handleBridgeRequest(recorder, {
      command: "assess", action: proposal, policyMode: "point-only"
    }).assessment;
    assert.deepEqual(point, new FlightRecorder().assess(proposal, false));
    assert.equal(point.score, score);
    assert.equal(point.decision, decision);
    assert.equal(point.historyLength, 0);
  }
});

test("bridge rejects unknown policy modes without recording the proposal", () => {
  const recorder = new FlightRecorder();
  const proposal = action("bad-mode", "search_files");
  for (const policyMode of ["point", "", null, false]) {
    assert.throws(() => handleBridgeRequest(recorder, {
      command: "assess", action: proposal, policyMode
    }), /Unknown policy mode/);
  }
  assert.deepEqual(recorder.history(proposal.sessionId), []);
});

test("point-only fails closed on artifact dataFlow", () => {
  const recorder = new FlightRecorder();
  for (const dataFlow of [{ inputs: [], outputs: [] }, { inputs: ["missing"], outputs: [] }, null]) {
    assert.throws(() => handleBridgeRequest(recorder, {
      command: "assess", action: action("lineage", "upload", { dataFlow }), policyMode: "point-only"
    }), /does not support artifact dataFlow/);
  }
  assert.deepEqual(recorder.history("agentdojo-test"), []);
});
