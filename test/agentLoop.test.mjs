import test from "node:test";
import assert from "node:assert/strict";
import { runAgentLoop } from "../dist/agentLoop.js";
import { parseProposal } from "../dist/azureAgent.js";

function scripted(actions, contexts = []) {
  let index = 0;
  return async (context, sessionId) => {
    contexts.push(JSON.parse(context));
    return parseProposal({action: actions[index++] ?? "stop"}, sessionId);
  };
}
test("loop feeds actual synthetic outputs into subsequent proposals", async () => {
  const contexts = [];
  const result = await runAgentLoop({propose: scripted(["read_document","query_records","create_export","stop"], contexts), approve: async () => true});
  assert.equal(result.status, "model_stopped");
  assert.equal(result.executedCount, 3);
  assert.equal(contexts[1].events[0].output.documentId, "sandbox-document");
  assert.equal(contexts[2].events[1].output.records.length, 2);
  assert.equal(contexts[3].events[2].output.artifact.sensitivity, "Restricted");
  assert.equal(new Set(result.events.map(e => e.action.sessionId)).size, 1);
});
test("denied review does not execute or allow dependent proposals", async () => {
  const contexts = [];
  const result = await runAgentLoop({propose: scripted(["read_document","query_records","create_export"], contexts)});
  assert.equal(result.status, "review_denied");
  assert.equal(result.executedCount, 1);
  assert.equal(contexts.length, 2);
  assert.equal(result.events[1].executed, false);
  assert.equal(result.events[1].output, undefined);
});
test("scripted injection upload is blocked and never gets tool output", async () => {
  let approvals = 0;
  const result = await runAgentLoop({scenario:"injection", propose:scripted(["read_document","query_records","create_export","upload_export"]), approve:async () => { approvals++; return true; }});
  assert.equal(result.status, "policy_blocked");
  assert.equal(approvals, 2);
  assert.equal(result.executedCount, 3);
  assert.match(result.events[0].output.text, /ADMIN OVERRIDE/);
  assert.equal(result.events[3].output, undefined);
  assert.equal(result.events[3].approved, false);
});
test("model refusal is separate from policy blocking", async () => {
  const result = await runAgentLoop({scenario:"injection", propose:scripted(["read_document","stop"])});
  assert.equal(result.status, "model_stopped");
  assert.equal(result.events.some(e => e.assessment.decision === "Block"), false);
});
test("step cap and repeat guard bound model calls", async () => {
  const capped = await runAgentLoop({maxSteps:1, propose:scripted(["read_document","query_records"])});
  assert.equal(capped.status, "step_limit");
  const repeated = await runAgentLoop({propose:scripted(["read_document","read_document"])});
  assert.equal(repeated.status, "repeated_action");
  assert.equal(repeated.executedCount, 1);
});
test("missing prerequisites and invalid session cause no tool effects", async () => {
  const missing = await runAgentLoop({propose:scripted(["create_export"])});
  assert.equal(missing.status, "precondition_failed");
  assert.equal(missing.executedCount, 0);
  const wrong = await runAgentLoop({propose: async () => parseProposal({action:"read_document"}, "wrong")});
  assert.equal(wrong.status, "invalid_session");
  assert.equal(wrong.executedCount, 0);
});
test("proposal failure preserves prior audit events", async () => {
  let calls = 0;
  const result = await runAgentLoop({propose:async (context, sessionId) => {
    if (calls++) throw new Error("mock transport failure");
    return parseProposal({action:"read_document"}, sessionId);
  }});
  assert.equal(result.status, "proposal_error");
  assert.equal(result.executedCount, 1);
  assert.equal(result.events.length, 1);
});
