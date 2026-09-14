import test from "node:test";
import assert from "node:assert/strict";
import { LiveSessions } from "../dist/liveSessions.js";
import { runAgentLoop } from "../dist/agentLoop.js";
import { parseProposal } from "../dist/azureAgent.js";

function runner(actions) {
  return options => {
    let index = 0;
    return runAgentLoop({...options, propose:async (context, sessionId) =>
      parseProposal({action:actions[index++] ?? "stop"}, sessionId)});
  };
}
async function until(sessions, id, predicate) {
  const deadline = Date.now() + 1500;
  while (Date.now() < deadline) {
    const state = sessions.get(id);
    if (predicate(state)) return state;
    await new Promise(resolve => setTimeout(resolve, 2));
  }
  throw new Error("Session did not reach expected state");
}

test("browser approval belongs to exactly one pending action and executes once", async () => {
  const sessions = new LiveSessions(runner(["read_document","query_records","stop"]));
  const id = sessions.start("safe");
  const waiting = await until(sessions,id,s => s.status === "awaiting_approval");
  try {
    assert.equal(waiting.events.length, 1);
    assert.equal(waiting.pending.action.operation, "query");
    assert.equal(sessions.decide(id,"wrong-action",true), false);
    assert.equal(sessions.decide("wrong-run",waiting.pending.action.id,true), false);
    assert.equal(sessions.decide(id,waiting.pending.action.id,true), true);
    assert.equal(sessions.decide(id,waiting.pending.action.id,true), false);
    const done = await until(sessions,id,s => s.status === "model_stopped");
    assert.equal(done.events.length, 2);
    assert.equal(done.events[1].approved, true);
    assert.equal(done.events[1].executed, true);
  } finally { sessions.decide(id,waiting.pending.action.id,false); }
});

test("browser rejection records denial without synthetic query output", async () => {
  const sessions = new LiveSessions(runner(["read_document","query_records","create_export"]));
  const id = sessions.start("injection");
  const waiting = await until(sessions,id,s => s.pending);
  sessions.decide(id,waiting.pending.action.id,false);
  const done = await until(sessions,id,s => s.status === "review_denied");
  assert.equal(done.events[1].executed, false);
  assert.equal(done.events[1].output, undefined);
  assert.equal(done.pending, undefined);
});

test("unanswered browser approval expires without executing", async () => {
  const sessions = new LiveSessions(runner(["read_document","query_records"]), 15);
  const id = sessions.start("safe");
  const done = await until(sessions,id,s => s.status === "review_denied");
  assert.equal(done.events[1].executed, false);
  assert.equal(sessions.decide(id,done.events[1].action.id,true), false);
});

test("only one live run starts at a time and returned state is a copy", async () => {
  const sessions = new LiveSessions(runner(["read_document","query_records"]));
  const id = sessions.start("safe");
  assert.throws(() => sessions.start("injection"), /already active/);
  const waiting = await until(sessions,id,s => s.pending);
  const originalId = waiting.pending.action.id;
  waiting.pending.action.id = "tampered";
  waiting.events.length = 0;
  assert.equal(sessions.get(id).pending.action.id, originalId);
  assert.equal(sessions.get(id).events.length, 1);
  sessions.decide(id,originalId,false);
  await until(sessions,id,s => s.status === "review_denied");
  const next = sessions.start("injection");
  assert.notEqual(next,id);
  const nextWaiting = await until(sessions,next,s => s.pending);
  assert.notEqual(nextWaiting.sessionId,sessions.get(id).sessionId);
  sessions.decide(next,nextWaiting.pending.action.id,false);
  await until(sessions,next,s => s.status === "review_denied");
});

test("policy block exposes no browser approval and no upload result", async () => {
  const sessions = new LiveSessions(runner(["read_document","query_records","create_export","upload_export"]));
  const id = sessions.start("injection");
  for (const operation of ["query","create_export"]) {
    const state = await until(sessions,id,s => s.pending?.action.operation === operation);
    sessions.decide(id,state.pending.action.id,true);
  }
  const done = await until(sessions,id,s => s.status === "policy_blocked");
  assert.equal(done.pending, undefined);
  assert.equal(done.events.at(-1).executed, false);
  assert.equal(done.events.at(-1).output, undefined);
});
