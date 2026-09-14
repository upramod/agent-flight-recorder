import test from "node:test";
import assert from "node:assert/strict";
import { buildSessionTrace } from "../dashboard/sessionTrace.js";
const action = { id:"a1", sessionId:"s1", timestamp:"2026-09-14T00:00:00Z", tool:"exporter", operation:"create_export",
 resourceType:"data_export", sensitivity:"Restricted", destinationTrust:"Trusted", privilegeLevel:4,
 inputProvenance:"TrustedTool", dataFlow:{inputs:["records"], outputs:["export"]}};
const assessment = {actionId:"a1", score:60, reasons:["restricted"], decision:"Review", historyLength:1};
test("live export preserves lineage, approval and output without configuration envelopes", () => {
 const trace = buildSessionTrace({mode:"live-azure",scenario:"safe",sessionId:"s1",status:"model_stopped",
 apiKey:"secret-test",events:[{action:{...action,apiKey:"secret-test"},assessment,executed:true,approved:true,output:{synthetic:true}}]});
 assert.equal(trace.mode,"live-azure");
 assert.equal(trace.events[0].approval.source,"human-review");
 assert.equal(trace.events[0].approval.approved,true);
 assert.deepEqual(trace.events[0].action.dataFlow.inputs,["records"]);
 assert.equal(JSON.stringify(trace).includes("secret-test"),false);
 trace.events[0].action.dataFlow.inputs[0]="mutated";
 assert.equal(action.dataFlow.inputs[0],"records");
});
test("pending review is not counted as executed", () => {
 const trace = buildSessionTrace({mode:"live-azure",status:"awaiting_approval",events:[],pending:{action,assessment,expiresAt:123}});
 assert.equal(trace.counts.assessed,1);
 assert.equal(trace.counts.executed,0);
 assert.equal(trace.pending.approval.outcome,"pending");
 assert.equal(trace.pending.executed,false);
});
test("scripted approval is never labeled human approval", () => {
 const trace=buildSessionTrace({mode:"scripted-replay",status:"replay_complete",events:[{...action,assessment,executed:true}]});
 assert.equal(trace.events[0].approval.source,"scripted");
 assert.equal(trace.events[0].approval.approved,true);
});
test("blocked upload and denied review retain distinct decisions without approval", () => {
 const trace=buildSessionTrace({mode:"live-azure",status:"policy_blocked",events:[
 {action,assessment,executed:false,approved:false},
 {action,assessment:{...assessment,decision:"Block",score:100},executed:false,approved:false}]});
 assert.equal(trace.counts.blocked,1);
 assert.equal(trace.counts.executed,0);
 assert.equal(trace.events[0].approval.outcome,"not-approved");
 assert.equal(trace.events[1].approval.outcome,"not-required");
});
