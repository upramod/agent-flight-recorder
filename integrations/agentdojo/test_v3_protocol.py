"""Outcome-free tests for v3 identity isolation and order balance."""
import copy
import json
import tempfile
import unittest
from collections import Counter
from itertools import permutations
from pathlib import Path

try:
    from .generate_v3_manifest import (ARMS, INJECTION_TASKS, MODEL_SLOTS, SEED,
                                       balanced_orders, build_manifest,
                                       prior_identities, validate_manifest)
    from .generate_v2_manifest import ident
except ImportError:
    from generate_v3_manifest import (ARMS, INJECTION_TASKS, MODEL_SLOTS, SEED,
                                      balanced_orders, build_manifest,
                                      prior_identities, validate_manifest)
    from generate_v2_manifest import ident


class V3ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = build_manifest()
        cls.excluded, _, _ = prior_identities()

    def test_selection_is_deterministic(self):
        self.assertEqual(self.manifest, build_manifest())
        self.assertEqual(json.dumps(self.manifest), json.dumps(build_manifest()))

    def test_all_prior_180_exact_identities_excluded(self):
        self.assertEqual(len(self.excluded), 180)
        evaluation = {ident(case) for case in self.manifest['pairs']}
        self.assertEqual(len(evaluation), 28)
        self.assertFalse(evaluation & self.excluded)
        self.assertEqual(Counter(i for _, i in evaluation), Counter({i: 2 for i in INJECTION_TASKS}))

    def test_development_is_disjoint_and_covers_all_goals(self):
        evaluation = {ident(case) for case in self.manifest['pairs']}
        development = {ident(case) for case in self.manifest['developmentPairs']}
        self.assertEqual(len(development), 14)
        self.assertFalse(development & (evaluation | self.excluded))
        self.assertEqual(Counter(i for _, i in development), Counter({i: 1 for i in INJECTION_TASKS}))

    def test_clean_users_appear_exactly_once(self):
        users = [case['userTask'] for case in self.manifest['cleanTasks']]
        self.assertEqual(len(users), 40)
        self.assertEqual(set(users), {f'user_task_{i}' for i in range(40)})

    def test_schedules_balance_permutations_and_positions(self):
        for count in range(1, 50):
            for model in MODEL_SLOTS:
                orders = balanced_orders(count, model, 'test')
                self.assertEqual(len(orders), count)
                frequencies = Counter(map(tuple, orders))
                counts = [frequencies[order] for order in permutations(ARMS)]
                self.assertLessEqual(max(counts) - min(counts), 1)
                for position in range(3):
                    counts = Counter(order[position] for order in orders)
                    self.assertLessEqual(max(counts[a] for a in ARMS) - min(counts[a] for a in ARMS), 1)

    def test_model_slots_have_independent_deterministic_order(self):
        for field in ('pairs', 'developmentPairs', 'cleanTasks'):
            a = [case['armOrderByModel']['model-a'] for case in self.manifest[field]]
            b = [case['armOrderByModel']['model-b'] for case in self.manifest[field]]
            self.assertNotEqual(a, b)

    def test_seed_change_is_explicit_and_still_excludes_prior(self):
        changed = build_manifest(SEED + 1)
        self.assertNotEqual(self.manifest['pairs'], changed['pairs'])
        validate_manifest(changed, self.excluded)

    def test_supplied_v2_manifest_must_match_exact_frozen_identities(self):
        from_prior = set()
        here = Path(__file__).resolve().parent
        for name in ('benchmark-manifest.json', 'holdout-manifest.json'):
            from_prior.update(ident(case) for case in json.loads((here / name).read_text())['pairs'])
        v2 = self.excluded - from_prior
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'v2.json'
            path.write_text(json.dumps({'cases': [{'user_task_id': u, 'injection_task_id': i} for u, i in sorted(v2)]}))
            verified = build_manifest(v2_manifest=path)
            self.assertIn('suppliedManifestSha256', verified['selection']['v2Exclusion'])
            document = json.loads(path.read_text())
            document['cases'][0] = document['cases'][1]
            path.write_text(json.dumps(document))
            with self.assertRaisesRegex(ValueError, 'frozen reconstruction'):
                build_manifest(v2_manifest=path)

    def test_overlap_and_unbalanced_orders_fail_validation(self):
        changed = copy.deepcopy(self.manifest)
        changed['developmentPairs'][0].update({key: changed['pairs'][0][key] for key in ('userTask', 'injectionTask')})
        with self.assertRaisesRegex(ValueError, 'development identity'):
            validate_manifest(changed, self.excluded)
        changed = copy.deepcopy(self.manifest)
        for case in changed['pairs']:
            case['armOrderByModel']['model-a'] = list(ARMS)
        with self.assertRaisesRegex(ValueError, 'permutations'):
            validate_manifest(changed, self.excluded)

    def test_adaptive_budget_and_unavailable_models_are_explicit(self):
        self.assertEqual(self.manifest['adaptive']['maxAttempts'], 5)
        self.assertTrue(self.manifest['adaptive']['campaignIsExperimentalUnit'])
        self.assertEqual(self.manifest['plannedTargetExecutionCeilings']['evaluationTotal'], 1248)
        self.assertIn('not_run', self.manifest['modelAvailabilityPolicy'])
        self.assertEqual(self.manifest['status'], 'generated-awaiting-freeze')


if __name__ == '__main__':
    unittest.main()
