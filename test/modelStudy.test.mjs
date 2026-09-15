import test from "node:test";
import assert from "node:assert/strict";
import { runModelStudy } from "../dist/modelStudy.js";

function fakeResult(scenario) {
  const blocked = scenario === "injection";
  return {
    mode: "azure-agent-synthetic-tools",
    scenario,
    sessionId: "session-" + scenario,
    status: blocked ? "policy_blocked" : "model_stopped",
    proposalCount: blocked ? 4 : 2,
    executedCount: blocked ? 3 : 1,
    events: blocked
      ? [{
          action: { id: "upload", sessionId: "session-" + scenario, timestamp: "2026-01-01T00:00:00.000Z",
            tool: "network", operation: "upload", resourceType: "data_export", sensitivity: "Restricted",
            destinationTrust: "Untrusted", privilegeLevel: 4, inputProvenance: "TrustedTool" },
          assessment: { actionId: "upload", score: 100, reasons: ["blocked"], decision: "Block", historyLength: 3 },
          executed: false,
          approved: false
        }]
      : []
  };
}

test("model study labels scripted approvals and separates terminal states", async () => {
  const rows = await runModelStudy({
    runsPerScenario: 2,
    scenarios: ["safe", "injection"],
    delayMs: 0,
    deployment: "test-deployment",
    runLoop: async options => fakeResult(options.scenario)
  });

  assert.equal(rows.length, 4);
  assert.ok(rows.every(row => row.approvalPolicy === "approve_all_reviews_scripted"));
  assert.ok(rows.filter(row => row.scenario === "safe").every(row => row.status === "model_stopped"));
  assert.ok(rows.filter(row => row.scenario === "injection").every(row =>
    row.status === "policy_blocked" && row.blockedOperation === "upload"
  ));
});

test("model study rejects invalid run counts and scenarios before model calls", async () => {
  let calls = 0;
  const runLoop = async () => {
    calls++;
    return fakeResult("safe");
  };

  await assert.rejects(
    runModelStudy({ runsPerScenario: 0, runLoop }),
    /positive integer/
  );
  await assert.rejects(
    runModelStudy({ runsPerScenario: 1, scenarios: ["unknown"], runLoop }),
    /Unknown model-study scenario/
  );
  assert.equal(calls, 0);
});
