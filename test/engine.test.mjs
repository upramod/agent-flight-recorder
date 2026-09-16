import test from "node:test";
import assert from "node:assert/strict";
import { FlightRecorder } from "../dist/engine.js";
import { ExecutionGate } from "../dist/gate.js";

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

test("treats AgentDojo external tool output as untrusted input", () => {
  const recorder = new FlightRecorder();
  const result = recorder.assess(action("external", {
    inputProvenance: "External",
    sensitivity: "Internal"
  }));
  assert.equal(result.score, 20);
  assert.ok(result.reasons.some(reason => reason.includes("external system")));
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

test("does not execute a blocked action", () => {
  const gate = new ExecutionGate(new FlightRecorder());
  let toolCalled = false;
  const result = gate.evaluate(action("blocked", {
    operation: "upload",
    sensitivity: "Restricted",
    destinationTrust: "Untrusted",
    privilegeLevel: 4
  }), () => {
    toolCalled = true;
    return "should never be returned";
  });

  assert.equal(result.assessment.decision, "Block");
  assert.equal(result.executed, false);
  assert.equal(toolCalled, false);
});

test("requires approval before executing a review action", () => {
  const gate = new ExecutionGate(new FlightRecorder());
  const actionToReview = action("review", {
    operation: "query",
    resourceType: "customer_records",
    sensitivity: "Restricted",
    privilegeLevel: 4
  });

  const pending = gate.evaluate(actionToReview, () => "executed");
  assert.equal(pending.approvalRequired, true);
  assert.equal(pending.executed, false);

  const approved = gate.evaluate(action("approved", {
    operation: "query",
    resourceType: "customer_records",
    sensitivity: "Restricted",
    privilegeLevel: 4
  }), () => "executed", true);
  assert.equal(approved.executed, true);
  assert.equal(approved.output, "executed");
});
