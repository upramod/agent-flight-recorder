import test from "node:test";
import assert from "node:assert/strict";
import { parseProposal, proposeAzureAction } from "../dist/azureAgent.js";
import { ExecutionGate } from "../dist/gate.js";
import { FlightRecorder } from "../dist/engine.js";

test("model cannot set security labels or propose unknown tools", () => {
  for (const value of [null, [], {}, {action:"shell"}, {action:"__proto__"}, {action:"upload_export", sensitivity:"Public"}]) {
    assert.throws(() => parseProposal(value, "s1"));
  }
  assert.equal(parseProposal({action:"upload_export"}, "s1").sensitivity, "Restricted");
  assert.equal(parseProposal({action:"stop"}, "s1"), null);
});

test("Azure proposal still passes through the gate", () => {
  const recorder = new FlightRecorder();
  const gate = new ExecutionGate(recorder);
  let executions = 0;
  const review = gate.evaluate(parseProposal({action:"query_records"}, "s1"), () => ++executions);
  assert.equal(review.approvalRequired, true);
  const blocked = gate.evaluate(parseProposal({action:"upload_export"}, "s1"), () => ++executions, true);
  assert.equal(blocked.assessment.decision, "Block");
  assert.equal(executions, 0);
  assert.equal(recorder.history("s1").length, 0);
});

const env = {AZURE_OPENAI_ENDPOINT:"https://example.openai.azure.com", AZURE_OPENAI_API_KEY:"fake-test-key", AZURE_OPENAI_DEPLOYMENT:"test-deployment"};
test("adapter validates a mocked Azure response without network", async () => {
  const transport = async (url, options) => {
    assert.equal(String(url), "https://example.openai.azure.com/openai/v1/chat/completions");
    assert.equal(options.redirect, "error");
    assert.equal(JSON.parse(options.body).model, "test-deployment");
    return new Response(JSON.stringify({choices:[{finish_reason:"stop", message:{content:'{"action":"read_document"}'}}]}));
  };
  const action = await proposeAzureAction("synthetic context", "s1", transport, env);
  assert.equal(action.operation, "read");
  assert.equal(action.sessionId, "s1");
});
test("missing config and invalid endpoint make no request", async () => {
  const transport = async () => { throw new Error("must not call"); };
  await assert.rejects(proposeAzureAction("x", "s1", transport, {}), /configuration/);
  await assert.rejects(proposeAzureAction("x", "s1", transport, {...env, AZURE_OPENAI_ENDPOINT:"https://example.com"}), /endpoint/);
});
test("HTTP failure and malformed model output fail closed", async () => {
  await assert.rejects(proposeAzureAction("x", "s1", async () => new Response("", {status:429}), env), /429/);
  await assert.rejects(proposeAzureAction("x", "s1", async () => new Response(JSON.stringify({choices:[{finish_reason:"stop",message:{content:"not JSON"}}]})), env));
});
