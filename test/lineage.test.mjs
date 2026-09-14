import test from "node:test";
import assert from "node:assert/strict";
import { FlightRecorder } from "../dist/engine.js";
import { ExecutionGate } from "../dist/gate.js";
import { scenarios } from "../dist/scenario.js";
const base = (id, operation, sensitivity, inputs, outputs, sessionId="s") => ({
 id, sessionId, timestamp:new Date().toISOString(), tool:"synthetic", operation,
 sensitivity, destinationTrust:operation==="upload"?"Untrusted":"Trusted",
 resourceType:"data_export", privilegeLevel:1, inputProvenance:"System", dataFlow:{inputs,outputs}
});
test("unrelated public upload allowed and restricted upload blocked in same session", () => {
 const gate = new ExecutionGate(new FlightRecorder());
 const results = scenarios.lineage.map(a => gate.evaluate(a, () => true, true));
 assert.equal(results[4].assessment.decision,"Allow");
 assert.equal(results[4].executed,true);
 assert.equal(results[5].assessment.decision,"Block");
 assert.equal(results[5].executed,false);
 assert.equal(results[1].assessment.effectiveSensitivity,"Restricted");
});
test("multi-generation export cannot lower sensitivity and joins take strongest source", () => {
 const r=new FlightRecorder(), g=new ExecutionGate(r);
 for (const a of [
 base("1","query","Restricted",[],["r"]),
 base("2","read","Public",[],["p"]),
 base("3","create_export","Public",["r","p"],["e1"]),
 base("4","create_export","Public",["e1"],["e2"])
 ]) assert.equal(g.evaluate(a,()=>true,true).executed,true);
 const assessment=r.assess(base("5","upload","Public",["e2"],[]),false);
 assert.equal(assessment.decision,"Block");
 assert.equal(assessment.effectiveSensitivity,"Restricted");
 assert.ok(assessment.sourceArtifactIds.includes("r"));
});
test("denied query never registers an artifact even with later approval", () => {
 const r=new FlightRecorder(), g=new ExecutionGate(r);
 const query={...base("1","query","Restricted",[],["r"]),privilegeLevel:4};
 assert.equal(g.evaluate(query,()=>true).executed,false);
 assert.equal(g.evaluate(base("2","create_export","Public",["r"],["e"]),()=>true,true).executed,false);
 assert.equal(r.history("s").length,0);
});
test("unknown and cross-session artifacts fail closed", () => {
 const r=new FlightRecorder(), g=new ExecutionGate(r);
 g.evaluate(base("1","read","Public",[],["p"]),()=>true);
 for (const a of [base("2","upload","Public",["missing"],[]),base("3","upload","Public",["p"],[],"other")]) {
  assert.equal(g.evaluate(a,()=>{throw new Error("must not execute");},true).assessment.decision,"Block");
 }
});
test("duplicate output IDs and missing input declarations are blocked", () => {
 const g=new ExecutionGate(new FlightRecorder());
 g.evaluate(base("1","query","Restricted",[],["r"]),()=>true,true);
 assert.equal(g.evaluate(base("2","read","Public",[],["r"]),()=>true,true).executed,false);
 assert.equal(g.evaluate(base("3","upload","Public",[],[]),()=>true,true).executed,false);
});
test("assessment alone and failed executors do not create provenance", () => {
 const r=new FlightRecorder(), g=new ExecutionGate(r);
 const a=base("1","read","Public",[],["p"]);
 r.assess(a);
 assert.equal(r.history("s").length,0);
 assert.throws(()=>g.evaluate(a,()=>{throw new Error("tool failed");}));
 assert.equal(r.assess(base("2","upload","Public",["p"],[])).decision,"Block");
});
test("executor and returned history mutations cannot alter stored provenance", () => {
 const r=new FlightRecorder(), g=new ExecutionGate(r);
 g.evaluate(base("1","query","Restricted",[],["r"]),a=>{a.sensitivity="Public";a.dataFlow.outputs[0]="changed";},true);
 const history=r.history("s");history[0].sensitivity="Public";
 assert.equal(r.assess(base("2","upload","Public",["r"],[])).effectiveSensitivity,"Restricted");
});
