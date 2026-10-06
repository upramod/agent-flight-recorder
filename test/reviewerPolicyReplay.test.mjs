import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { analyze, replay } from '../scripts/reviewer_policy_replay.mjs';

const action = (id, overrides={}) => ({id,sessionId:'s',timestamp:'2026-10-06',
  tool:'fixture',operation:'read',resourceType:'records',sensitivity:'Public',
  destinationTrust:'Trusted',privilegeLevel:1,inputProvenance:'System',...overrides});
const event = (a, executed, decision='Allow', score=0) => ({tool:a.operation,action:a,
  executed,assessment:{decision,score}});

test('counterfactual permission never adds a denied action to observed history', () => {
  const rows = replay([
    event(action('denied', {inputProvenance:'External'}),false,'Review',20),
    event(action('later',{sensitivity:'Restricted'}),true,'Allow',25)
  ],'full',10,70);
  assert.equal(rows[0].decision,'Review');
  assert.equal(rows[1].score,25);
});

test('observed effects remain history when an alternate threshold would deny them', () => {
  const events = [event(action('read',{inputProvenance:'External'}),true,'Allow',20),
    event(action('sensitive',{sensitivity:'Restricted'}),false,'Review',45)];
  assert.equal(replay(events,'full',10,70)[1].score,45);
  assert.equal(replay(events,'without_history')[1].score,25);
  assert.equal(replay(events,'without_provenance')[1].score,25);
});

test('invalid lineage stays blocked even at permissive sweep thresholds', () => {
  const events = [event(action('missing',{dataFlow:{inputs:['absent'],outputs:[]}}),false,'Block',100)];
  assert.equal(replay(events,'full',90,100)[0].decision,'Block');
});

test('threshold inputs cannot silently change experiment semantics', () => {
  assert.throws(() => replay([], 'full',70,40),/Invalid thresholds/);
  assert.throws(() => replay([], 'unknown'),/Unknown variant/);
});

function auditDirectory(t, events) {
  const root = mkdtempSync(join(tmpdir(), 'afr-policy-replay-'));
  t.after(() => rmSync(root, {recursive:true, force:true}));
  writeFileSync(join(root, 'flight-recorder-policy.jsonl'),
    events.map(event => JSON.stringify(event)).join('\n')+'\n');
  return root;
}

test('analysis rejects auxiliary and attacked sessions combined in one audit', t => {
  const root = auditDirectory(t, [
    event(action('auxiliary', {sessionId:'auxiliary'}),true),
    event(action('attacked', {sessionId:'attacked'}),true)
  ]);
  assert.throws(() => analyze(root), /one identified session.*extract_attacked_audits/);
});

test('analysis rejects an audit without an explicit session identifier', t => {
  const root = auditDirectory(t, [event(action('missing', {sessionId:undefined}),true)]);
  assert.throws(() => analyze(root), /one identified session/);
});

test('analysis retains a validated single attacked session and frozen parity', t => {
  const root = auditDirectory(t, [event(action('attacked'),true)]);
  const result = analyze(root);
  assert.equal(result.trajectories,1);
  assert.equal(result.conditions[0].proposals,1);
  assert.deepEqual(result.parity,{scoreMismatches:0,decisionMismatches:0});
});
