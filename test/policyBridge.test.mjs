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
