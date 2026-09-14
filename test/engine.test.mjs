import test from "node:test";
import assert from "node:assert/strict";
import { FlightRecorder } from "../dist/engine.js";

const action = (id, overrides = {}) => ({
  id,
  sessionId: "test-session",
  timestamp: new Date().toISOString(),
  tool: "test",
  operation: "read",
  resourceType: "document",
  sensitivity: "Public",
  destinationTrust: "Trusted",
  privilegeLevel: 1,
  inputProvenance: "System",
  ...overrides
});

test("allows a low-risk action", () => {
  const result = new FlightRecorder().assess(action("a1"));
  assert.equal(result.decision, "Allow");
});

test("raises risk when untrusted input precedes restricted access", () => {
  const recorder = new FlightRecorder();
  recorder.assess(action("a1", { inputProvenance: "UntrustedDocument" }));
  const result = recorder.assess(action("a2", {
    operation: "query",
    resourceType: "customer_records",
    sensitivity: "Restricted",
    privilegeLevel: 4
  }));
  assert.equal(result.decision, "Review");
  assert.ok(result.reasons.some(reason => reason.includes("untrusted input")));
});

test("blocks an export upload after the attack trajectory", () => {
  const recorder = new FlightRecorder();
  recorder.assess(action("a1", { inputProvenance: "UntrustedDocument" }));
  recorder.assess(action("a2", {
    operation: "query",
    resourceType: "customer_records",
    sensitivity: "Restricted",
    privilegeLevel: 4
  }));
  recorder.assess(action("a3", {
    operation: "create_export",
    resourceType: "data_export",
    sensitivity: "Restricted",
    privilegeLevel: 4
  }));
  const result = recorder.assess(action("a4", {
    operation: "upload",
    resourceType: "data_export",
    sensitivity: "Restricted",
    destinationTrust: "Untrusted",
    privilegeLevel: 4
  }));
  assert.equal(result.decision, "Block");
  assert.ok(result.score >= 70);
});
