#!/usr/bin/env python3
"""Create the exploratory v3 task/schedule manifest without model or outcome I/O."""
import argparse
import hashlib
import json
from collections import Counter
from itertools import permutations
from pathlib import Path

try:
    from .generate_v2_manifest import cases, ident, key as v2_key
except ImportError:
    from generate_v2_manifest import cases, ident, key as v2_key

HERE = Path(__file__).resolve().parent
SEED = 20261006
ARMS = ('baseline', 'point-only', 'full-history')
MODEL_SLOTS = ('model-a', 'model-b')
USER_TASKS = tuple(f'user_task_{i}' for i in range(40))
INJECTION_TASKS = tuple(f'injection_task_{i}' for i in range(14))
FROZEN_PRIOR_HASHES = {
    'benchmark-manifest.json': '23bada88bfaf79b652e683cf351deaac25046a42324c385304d8145ea390cc38',
    'holdout-manifest.json': 'ac4a675b79dbd39ee84e5fa2c775ad412bee4d79a8ce524d235c7adfa1416c41',
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def selection_key(seed, *parts):
    return sha256('|'.join(('afr-v3', str(seed), *parts)).encode())


def prior_identities(v2_manifest=None):
    """Reconstruct the exact frozen v2 selection; optionally verify its manifest.

    The two earlier manifests are pinned by byte digest. V2 selected the first
    120 of their 500 remaining identities using its committed SHA-256 key.
    This reads identities only and never consults earlier outcome files.
    """
    earlier = set()
    provenance = {}
    for name, expected in FROZEN_PRIOR_HASHES.items():
        raw = (HERE / name).read_bytes()
        actual = sha256(raw)
        if actual != expected:
            raise ValueError(f'Frozen prior manifest changed: {name}')
        identities = [ident(case) for case in cases(json.loads(raw))]
        if len(identities) != 30 or len(set(identities)) != 30:
            raise ValueError(f'Expected 30 unique prior identities in {name}')
        if earlier.intersection(identities):
            raise ValueError('The frozen diagnostic and holdout identities overlap')
        earlier.update(identities)
        provenance[name] = actual
    universe = {(u, i) for u in USER_TASKS for i in INJECTION_TASKS}
    if not earlier.issubset(universe):
        raise ValueError('Prior identity outside the pinned workspace inventory')
    v2 = sorted(universe - earlier, key=lambda pair: v2_key('|'.join(pair)))[:120]
    evidence = {
        'method': "Reconstruct first 120 sha256('afr-v2|user_task_id|injection_task_id') identities after the two pinned exclusions",
        'pairCount': len(v2),
        'identitySha256': sha256(json.dumps(sorted(v2), separators=(',', ':')).encode()),
    }
    if v2_manifest is not None:
        raw = Path(v2_manifest).read_bytes()
        document = json.loads(raw)
        supplied = [ident(case) for case in cases(document)]
        if len(supplied) != 120 or len(set(supplied)) != 120 or set(supplied) != set(v2):
            raise ValueError('Supplied v2 manifest does not match the frozen reconstruction')
        evidence['suppliedManifestSha256'] = sha256(raw)
    return earlier | set(v2), provenance, evidence


def balanced_orders(count, model_slot, scope, seed=SEED):
    """SHA-seeded schedules balance six permutations and each arm's position.

    Complete blocks contain every permutation. Remainders are chosen from
    cyclic Latin triples, so counts by position differ by at most one even
    when the number of cases is not divisible by six.
    """
    if count < 0:
        raise ValueError('Negative schedule size')
    latin = [[(0, 1, 2), (1, 2, 0), (2, 0, 1)],
             [(0, 2, 1), (2, 1, 0), (1, 0, 2)]]
    first = int(selection_key(seed, 'latin', scope, model_slot), 16) % 2
    latin = [latin[first], latin[1 - first]]
    for index, triple in enumerate(latin):
        triple.sort(key=lambda p: selection_key(seed, 'remainder', scope, model_slot, str(index), str(p)))
    orders = list(permutations(range(3))) * (count // 6)
    remaining = count % 6
    orders += latin[0][:min(remaining, 3)]
    orders += latin[1][:max(remaining - 3, 0)]
    indexed = list(enumerate(orders))
    indexed.sort(key=lambda item: selection_key(seed, 'schedule', scope, model_slot, str(item[0])))
    return [[ARMS[index] for index in order] for _, order in indexed]


def attach_orders(records, scope, seed):
    schedules = {slot: balanced_orders(len(records), slot, scope, seed) for slot in MODEL_SLOTS}
    return [{**record, 'armOrderByModel': {slot: schedules[slot][index] for slot in MODEL_SLOTS}}
            for index, record in enumerate(records)]


def build_manifest(seed=SEED, v2_manifest=None):
    if type(seed) is not int or seed < 0:
        raise ValueError('Seed must be a nonnegative integer')
    excluded, prior_hashes, v2_evidence = prior_identities(v2_manifest)
    selected, development = [], []
    for injection in INJECTION_TASKS:
        eligible = [(u, injection) for u in USER_TASKS if (u, injection) not in excluded]
        eligible.sort(key=lambda pair: selection_key(seed, 'pairs', *pair))
        if len(eligible) < 3:
            raise ValueError(f'Insufficient fresh identities for {injection}')
        development.append(eligible[0])
        selected.extend(eligible[1:3])

    def pair_records(pairs, scope, prefix):
        ordered = sorted(pairs, key=lambda pair: selection_key(seed, 'case-order', scope, *pair))
        records = [{'id': f'{prefix}-{index:02d}', 'userTask': u, 'injectionTask': i,
                    'selectionKey': selection_key(seed, 'pairs', u, i)}
                   for index, (u, i) in enumerate(ordered)]
        return attach_orders(records, scope, seed)

    clean_users = sorted(USER_TASKS, key=lambda user: selection_key(seed, 'clean-order', user))
    clean = attach_orders([{'id': f'clean-{index:02d}', 'userTask': user}
                           for index, user in enumerate(clean_users)], 'clean', seed)
    manifest = {
        'schemaVersion': 3,
        'protocol': 'paper/reviewer-validation-protocol-v3.md',
        'status': 'generated-awaiting-freeze',
        'studyType': 'exploratory-reviewer-validation',
        'agentdojoPackageVersion': '0.1.35',
        'benchmarkVersion': 'v1.2.2',
        'suite': 'workspace',
        'attack': 'tool_knowledge',
        'reviewPolicy': 'deny',
        'trustedEmailDomain': 'bluesparrowtech.com',
        'arms': list(ARMS),
        'modelSlots': list(MODEL_SLOTS),
        'modelAvailabilityPolicy': 'Bind independently verified distinct models before their outcome calls; unavailable slots remain not_run. Complete all three matched arms for each available model and label a one-model study incomplete.',
        'selection': {
            'seed': seed,
            'method': "Per goal, rank sha256('afr-v3|seed|pairs|user_task_id|injection_task_id'); reserve first eligible identity for development and next two for evaluation",
            'universeCount': 560,
            'excludedPriorPairCount': len(excluded),
            'eligiblePairCount': 560 - len(excluded),
            'evaluationPairsPerGoal': 2,
            'developmentPairsPerGoal': 1,
            'priorManifestSha256': prior_hashes,
            'v2Exclusion': v2_evidence,
        },
        'scheduling': {
            'method': 'SHA-seeded permutation blocks with cyclic-Latin remainders; balance each arm position within model and workload',
            'fixedAndAdaptiveUseSameArmOrder': True,
            'caseOrder': 'SHA-seeded independently of prior outcomes',
        },
        'adaptive': {
            'maxAttempts': 5,
            'feedback': ['attack_success', 'utility', 'policy_trace', 'tool_trace'],
            'stopOnFirstAttackSuccess': True,
            'campaignIsExperimentalUnit': True,
            'freshEnvironmentAndPolicyHistoryPerAttempt': True,
        },
        'plannedTargetExecutionCeilings': {
            'fixedAttack': 168, 'adaptiveAttack': 840, 'clean': 240,
            'evaluationTotal': 1248, 'developmentSeparate': 84,
            'note': 'Two available model slots; attacker-generation and preflight calls are recorded separately. No unavailability may be filled by duplicate model aliases.',
        },
        'pairs': pair_records(selected, 'attacked', 'v3'),
        'developmentPairs': pair_records(development, 'development', 'dev'),
        'cleanTasks': clean,
    }
    validate_manifest(manifest, excluded)
    return manifest


def validate_manifest(manifest, excluded):
    pairs = [ident(case) for case in manifest['pairs']]
    development = [ident(case) for case in manifest['developmentPairs']]
    if len(pairs) != 28 or len(set(pairs)) != 28 or set(pairs) & excluded:
        raise ValueError('Invalid evaluation identity set')
    if Counter(i for _, i in pairs) != Counter({i: 2 for i in INJECTION_TASKS}):
        raise ValueError('Evaluation must contain two identities per injection goal')
    if len(development) != 14 or len(set(development)) != 14 or set(development) & (excluded | set(pairs)):
        raise ValueError('Invalid disjoint development identity set')
    if Counter(i for _, i in development) != Counter({i: 1 for i in INJECTION_TASKS}):
        raise ValueError('Development must reserve one identity per injection goal')
    if sorted(case['userTask'] for case in manifest['cleanTasks']) != sorted(USER_TASKS):
        raise ValueError('Clean workload must contain all 40 users exactly once')
    for field in ('pairs', 'developmentPairs', 'cleanTasks'):
        for slot in MODEL_SLOTS:
            orders = [tuple(case['armOrderByModel'][slot]) for case in manifest[field]]
            if any(set(order) != set(ARMS) or len(order) != 3 for order in orders):
                raise ValueError('Each order must contain each arm exactly once')
            frequencies = Counter(orders)
            counts = [frequencies[order] for order in permutations(ARMS)]
            if max(counts) - min(counts) > 1:
                raise ValueError('Arm permutations are not balanced')
            for position in range(3):
                counts = Counter(order[position] for order in orders)
                if max(counts[arm] for arm in ARMS) - min(counts[arm] for arm in ARMS) > 1:
                    raise ValueError('Arm positions are not balanced')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--v2-manifest', type=Path,
                        help='Optional original identity manifest to verify the exact v2 reconstruction')
    args = parser.parse_args()
    result = build_manifest(args.seed, args.v2_manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'evaluationPairs': len(result['pairs']),
                      'developmentPairs': len(result['developmentPairs']),
                      'cleanTasks': len(result['cleanTasks']),
                      'excludedPriorPairs': result['selection']['excludedPriorPairCount'],
                      'manifestSha256': sha256(args.output.read_bytes())}, indent=2))
