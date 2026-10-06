"""Execute frozen reviewer-validation cells without auxiliary injection-task runs."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

from agentdojo.attacks.attack_registry import load_attack
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.agent_pipeline.llms.openai_llm import _function_to_openai
from adaptive_attack import generate_candidate, validate_injections, CandidateGenerationError
from model_preflight import client_for, deployment_for
from validation_target import run_target

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=lambda x: x.model_dump()) + '\n')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_for(preflight, slot):
    rows = [r for r in preflight['models'] if r['slot'] == slot and r['status'] == 'ready']
    if len(rows) != 1:
        return None
    if slot == 'model-b':
        primary = model_for(preflight, 'model-a')
        if primary and rows[0]['responseModel'] == primary['responseModel']:
            raise ValueError('Model-b is not a distinct response model')
    return rows[0]


def add_identity(result, case, slot, arm, manifest_hash, workload):
    return {**result, 'caseId': case['id'], 'userTask': case['userTask'],
            'injectionTask': None if workload == 'clean' else case.get('injectionTask'), 'modelSlot': slot,
            'arm': arm, 'manifestSha256': manifest_hash, 'workload': workload}


def fixed_payload(suite, case):
    attack = load_attack('tool_knowledge', suite, SimpleNamespace(name='gpt-4o-mini-2024-07-18'))
    payload = attack.attack(suite.get_user_task_by_id(case['userTask']),
                            suite.get_injection_task_by_id(case['injectionTask']))
    return validate_injections(payload, sorted(payload))


def adaptive_episode(config, attacker_config, arm, case, suite, payload, output, manifest_hash,
                     attempts=5, target_fn=run_target, generator_fn=generate_candidate):
    feedback, target_results = [], []
    episode = add_identity({'status': 'error', 'attack_success': None,
                            'first_attempt_utility': None, 'attempts': []},
                            case, config['slot'], arm, manifest_hash, 'adaptive')
    schema = [_function_to_openai(tool) for tool in suite.tools]
    catalog = json.loads((HERE / 'workspace-policy.json').read_text())
    history_rules = {'source': (ROOT / 'src/engine.ts').read_text(),
                    'arm': arm, 'reviewPolicy': 'deny',
                    'pointOnly': 'Same point scores/thresholds, empty history; no artifact links.',
                    'baseline': 'No policy enforcement; standard AgentDojo tool execution.',
                    'normalizationAndMetadata': (HERE / 'flight_recorder_executor.py').read_text(),
                    'trustedEmailDomain': 'bluesparrowtech.com'}
    for attempt in range(1, attempts + 1):
        location = output / f'attempt-{attempt:02d}'
        location.mkdir(parents=True, exist_ok=True)
        if attempt > 1:
            try:
                with client_for(attacker_config) as client:
                    candidate = generator_fn(client, deployment_for(attacker_config),
                        user_task=suite.get_user_task_by_id(case['userTask']).PROMPT,
                        injection_goal=suite.get_injection_task_by_id(case['injectionTask']).GOAL,
                        tool_schemas=schema, policy_catalog=catalog, history_rules=history_rules,
                        selected_arm=arm, allowed_vector_ids=sorted(payload),
                        previous_attempts=feedback, candidate_number=attempt)
                write_json(output / f'attacker-generation-{attempt:02d}.json', candidate.audit)
                if candidate.audit.get('response_model') != attacker_config['responseModel']:
                    episode['error'] = {'type': 'AttackerIdentityDrift', 'stage': 'attacker_generation'}
                    break
                payload = candidate.injections
            except CandidateGenerationError as error:
                write_json(output / f'attacker-generation-{attempt:02d}.json', error.audit)
                episode['error'] = {'type': type(error).__name__, 'stage': 'attacker_generation'}
                break
        write_json(location / 'injections.json', payload)
        result = target_fn(config, arm, case['userTask'], case['injectionTask'], payload, location, manifest_hash)
        result = add_identity(result, case, config['slot'], arm, manifest_hash, 'adaptive')
        result['attempt'] = attempt
        write_json(location / 'result.json', result)
        target_results.append({k: result.get(k) for k in ('attempt', 'status', 'utility', 'attack_success', 'error')})
        episode['attempts'] = target_results
        if result['status'] != 'completed':
            episode['error'] = {'type': 'TargetExecutionError', 'stage': 'target', 'details': result.get('error')}
            break
        if attempt == 1:
            episode['first_attempt_utility'] = result['utility']
        feedback.append({'injections': payload, 'attack_success': result['attack_success'],
                         'utility': result['utility'], 'tool_messages': result['tool_messages'],
                         'policy_denials': result['policy_denials']})
        if result['attack_success'] or attempt == attempts:
            episode.update(status='completed', attack_success=any(r['attack_success'] for r in feedback))
            break
    episode['attackerModel'] = attacker_config['responseModel']
    episode['targetModel'] = config['responseModel']
    episode['maximumAttempts'] = attempts
    write_json(output / 'episode.json', episode)
    return episode


def run(options):
    manifest = json.loads(options.manifest.read_text())
    preflight = json.loads(options.preflight.read_text())
    manifest_hash = sha256(options.manifest)
    config = model_for(preflight, options.model_slot)
    output = options.output
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a fresh output directory; never overwrite a recorded execution')
    output.mkdir(parents=True, exist_ok=True)
    freeze = {'manifestSha256': manifest_hash, 'preflightSha256': sha256(options.preflight),
              'gitSha': os.getenv('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              'githubRunId': os.getenv('GITHUB_RUN_ID'), 'workload': options.workload,
              'modelSlot': options.model_slot, 'shard': options.shard, 'shards': options.shards,
              'development': options.development, 'maximumAttempts': options.max_attempts,
              'catalogSha256': sha256(HERE/'workspace-policy.json'),
              'engineSha256': sha256(ROOT/'src/engine.ts'),
              'resourceLimits': {'shardReportedTokens': 3000000, 'requestPromptCharacters': 500000,
                  'targetCalls': 48, 'targetCompletionTokens': 2048, 'targetTemperature': 0,
                  'attackerCompletionTokens': 5000, 'attackerTemperature': 0.7, 'transportRetries': 0}}
    write_json(output / 'freeze.json', freeze)
    if config is None:
        write_json(output / 'not-run.json', {'status': 'not_run', 'reason': 'Model slot unavailable', **freeze})
        return
    if not options.development and options.max_attempts != manifest['adaptive']['maxAttempts']:
        raise ValueError('Evaluation attempt budget must match the frozen manifest')
    if not 1 <= options.max_attempts <= 5 or not 0 <= options.shard < options.shards:
        raise ValueError('Invalid budget or shard')
    suite = get_suite(manifest['benchmarkVersion'], manifest['suite'])
    attacker = model_for(preflight, 'model-a')
    source = 'developmentPairs' if options.development else ('cleanTasks' if options.workload == 'clean' else 'pairs')
    cases = [c for i,c in enumerate(manifest[source]) if i % options.shards == options.shard]
    if options.limit:
        if not options.development:
            raise ValueError('Evaluation may not reduce the frozen sample')
        cases = cases[:options.limit]
    for case in cases:
        payload = {} if options.workload == 'clean' else fixed_payload(suite, case)
        for arm in case['armOrderByModel'][options.model_slot]:
            location = output / options.model_slot / options.workload / case['id'] / arm
            if options.workload == 'adaptive':
                result = adaptive_episode(config, attacker, arm, case, suite, payload, location,
                                          manifest_hash, options.max_attempts)
            else:
                write_json(location / 'injections.json', payload)
                result = run_target(config, arm, case['userTask'],
                                    None if options.workload == 'clean' else case['injectionTask'],
                                    payload, location, manifest_hash)
                result = add_identity(result, case, options.model_slot, arm, manifest_hash, options.workload)
                write_json(location / 'result.json', result)
            print(json.dumps({k: result.get(k) for k in ('caseId','modelSlot','arm','workload','status','utility','attack_success')}), flush=True)
    write_json(output / 'finished.json', {'status': 'finished', 'casesAttempted': len(cases), **freeze})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--preflight', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model-slot', choices=['model-a','model-b'], required=True)
    parser.add_argument('--workload', choices=['fixed','adaptive','clean'], required=True)
    parser.add_argument('--shard', type=int, default=0)
    parser.add_argument('--shards', type=int, default=1)
    parser.add_argument('--development', action='store_true')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--max-attempts', type=int, default=5)
    run(parser.parse_args())
