"""Tests for v3 paired denominators, campaigns, and missing-data handling."""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

try:
    from .analyze_validation_v3 import analyze, cluster_summary, percentile
except ImportError:
    from analyze_validation_v3 import analyze, cluster_summary, percentile


class V3AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.results = self.root / 'results'
        self.manifest = {'schemaVersion': 3, 'arms': ['baseline', 'point-only', 'full-history'],
                         'modelSlots': ['model-a', 'model-b'], 'adaptive': {'maxAttempts': 5},
                         'pairs': [{'id': 'v3-00', 'userTask': 'user_task_0', 'injectionTask': 'injection_task_0'},
                                   {'id': 'v3-01', 'userTask': 'user_task_1', 'injectionTask': 'injection_task_1'}],
                         'cleanTasks': [{'id': 'clean-00', 'userTask': 'user_task_0'}]}
        self.manifest_path = self.root / 'manifest.json'
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.digest = hashlib.sha256(self.manifest_path.read_bytes()).hexdigest()

    def record(self, workload, case, arm, utility=None, attack=None, status='completed', model='model-a'):
        return {'status': status, 'utility': utility, 'attack_success': attack,
                'caseId': case['id'], 'userTask': case['userTask'],
                'injectionTask': case.get('injectionTask'), 'arm': arm, 'modelSlot': model,
                'manifestSha256': self.digest}

    def write(self, workload, case, arm, record, attempt=None):
        directory = self.results / record['modelSlot'] / workload / case['id'] / arm
        if attempt is not None:
            directory /= f'attempt-{attempt:02d}'
        directory.mkdir(parents=True, exist_ok=True)
        filename = 'episode.json' if workload == 'adaptive' and attempt is None else 'result.json'
        (directory / filename).write_text(json.dumps(record))
        return directory / filename

    def analyze(self):
        return analyze(self.manifest_path, self.results, replicates=200, seed=20261007)

    @staticmethod
    def phase(result, workload, model='model-a'):
        return next(a for a in result['analyses'] if a['modelSlot'] == model and a['workload'] == workload)

    def test_missing_models_and_cells_are_not_resistance(self):
        result = self.analyze()
        self.assertEqual(result['plannedCellCount'], 30)
        self.assertEqual(result['cellStatusCounts'], {'missing': 30})
        self.assertEqual(result['modelStatus'], {'model-a': 'not_run', 'model-b': 'not_run'})
        rate = self.phase(result, 'fixed')['byArm']['baseline']['endpoints']['attack_success']
        self.assertEqual(rate['valid'], 0)
        self.assertIsNone(rate['rateAmongValid'])
        self.assertEqual(rate['plannedDenominatorBinaryBounds'], [0, 1])

    def test_paired_outcomes_and_sign_are_preserved(self):
        for index, case in enumerate(self.manifest['pairs']):
            for arm in self.manifest['arms']:
                attack = arm != 'full-history' and index == 0
                utility = arm != 'full-history' or index == 1
                self.write('fixed', case, arm, self.record('fixed', case, arm, utility, attack))
        result = self.analyze()
        fixed = self.phase(result, 'fixed')
        comparison = next(c for c in fixed['pairedComparisons'] if c['primaryContrast'] and c['endpoint'] == 'attack_success')
        self.assertEqual(comparison['validPairedCount'], 2)
        self.assertEqual(comparison['riskDifferenceAmongValidPairs'], -.5)
        self.assertEqual(comparison['pairedTableArmComparator'], {'00': 1, '01': 1, '10': 0, '11': 0})
        self.assertEqual(comparison['plannedPairDifferenceBounds'], [-.5, -.5])
        self.assertEqual(comparison['taskComponentSensitivity']['injectionTask']['clusterCount'], 2)
        self.assertEqual(self.analyze(), result)

    def test_bad_digest_and_error_are_separate_from_valid_false_outcomes(self):
        case = self.manifest['pairs'][0]
        record = self.record('fixed', case, 'baseline', False, False)
        record['manifestSha256'] = 'wrong'
        self.write('fixed', case, 'baseline', record)
        self.write('fixed', case, 'point-only', self.record('fixed', case, 'point-only', status='error'))
        result = self.analyze()
        self.assertEqual(self.phase(result, 'fixed')['statusCounts'], {'invalid': 1, 'error': 1, 'missing': 4})
        self.assertEqual(self.phase(result, 'fixed')['byArm']['baseline']['endpoints']['attack_success']['valid'], 0)

    def test_partial_pair_binary_bounds_keep_planned_denominator(self):
        case = self.manifest['pairs'][0]
        self.write('fixed', case, 'point-only', self.record('fixed', case, 'point-only', True, True))
        comparison = next(c for c in self.phase(self.analyze(), 'fixed')['pairedComparisons']
                          if c['primaryContrast'] and c['endpoint'] == 'attack_success')
        self.assertEqual(comparison['validPairedCount'], 0)
        self.assertEqual(comparison['plannedPairDifferenceBounds'], [-1, .5])

    def campaign(self, arm, successes, completed=True, first_utility=True):
        case = self.manifest['pairs'][0]
        for index, success in enumerate(successes, 1):
            self.write('adaptive', case, arm, self.record('adaptive', case, arm, first_utility, success), attempt=index)
        episode = self.record('adaptive', case, arm, attack=any(successes) if completed else None,
                              status='completed' if completed else 'error')
        episode.update(first_attempt_utility=first_utility if successes else None,
                       attempts=[{'attempt': index} for index in range(1, len(successes) + 1)])
        return self.write('adaptive', case, arm, episode)

    def test_adaptive_attempts_form_one_campaign(self):
        self.campaign('baseline', [False, True])
        self.campaign('point-only', [False] * 5)
        self.campaign('full-history', [False] * 5)
        adaptive = self.phase(self.analyze(), 'adaptive')
        rate = adaptive['byArm']['baseline']['endpoints']['attack_success']
        self.assertEqual((rate['successes'], rate['valid'], rate['planned']), (1, 1, 2))
        self.assertTrue(all(c['endpoint'] == 'attack_success' for c in adaptive['pairedComparisons']))
        comparison = next(c for c in adaptive['pairedComparisons'] if c['armMinusComparator'] == 'full-history minus baseline')
        self.assertEqual(comparison['validPairedCount'], 1)
        self.assertEqual(comparison['riskDifferenceAmongValidPairs'], -1)

    def test_early_unsuccessful_completed_campaign_is_invalid(self):
        self.campaign('baseline', [False, False])
        result = self.analyze()
        adaptive = self.phase(result, 'adaptive')
        self.assertEqual(adaptive['statusCounts']['invalid'], 1)
        self.assertEqual(adaptive['byArm']['baseline']['endpoints']['attack_success']['valid'], 0)

    def test_incomplete_campaign_retains_only_valid_first_attempt_utility(self):
        self.campaign('baseline', [False], completed=False, first_utility=False)
        adaptive = self.phase(self.analyze(), 'adaptive')
        self.assertEqual(adaptive['byArm']['baseline']['endpoints']['attack_success']['valid'], 0)
        self.assertEqual(adaptive['byArm']['baseline']['endpoints']['first_attempt_utility']['valid'], 1)
        self.assertEqual(adaptive['statusCounts']['error'], 1)

    def test_stopping_after_a_prior_success_is_invalid(self):
        self.campaign('baseline', [True, False])
        adaptive = self.phase(self.analyze(), 'adaptive')
        self.assertEqual(adaptive['statusCounts']['invalid'], 1)

    def test_clean_attack_endpoint_is_null_and_user_resampling_is_paired(self):
        case = self.manifest['cleanTasks'][0]
        for arm in self.manifest['arms']:
            self.write('clean', case, arm, self.record('clean', case, arm, arm != 'full-history'))
        clean = self.phase(self.analyze(), 'clean')
        comparison = next(c for c in clean['pairedComparisons'] if c['primaryContrast'])
        self.assertEqual(comparison['riskDifferenceAmongValidPairs'], -1)
        self.assertEqual(set(comparison['taskComponentSensitivity']), {'userTask'})
        self.assertTrue(comparison['taskComponentSensitivity']['userTask']['degenerate'])
        self.assertNotIn('attack_success', clean['byArm']['baseline']['endpoints'])

    def test_percentiles_and_degenerate_cluster_warning(self):
        self.assertEqual(percentile([0, 10], .25), 2.5)
        result = cluster_summary([{'userTask': 'same', 'difference': 0}], 'userTask', 'test', 20, 4)
        self.assertEqual(result['percentile95'], [0, 0])
        self.assertTrue(result['degenerate'])
        self.assertIn('not equivalence', result['interpretation'])

    def test_nested_shards_find_cells_and_preserve_adaptive_attempts(self):
        case = self.manifest['pairs'][0]
        self.write('fixed', case, 'baseline', self.record('fixed', case, 'baseline', True, False))
        self.campaign('full-history', [False] * 5)
        nested = self.results / 'downloaded-artifact' / 'shard-03'
        nested.mkdir(parents=True)
        shutil.move(str(self.results / 'model-a'), nested / 'model-a')
        result = self.analyze()
        self.assertEqual(result['cellStatusCounts'], {'completed': 2, 'missing': 28})
        self.assertEqual(self.phase(result, 'adaptive')['byArm']['full-history']['endpoints']['attack_success']['valid'], 1)
        self.assertEqual(result['unplannedCellDirectories'], [])

    def test_duplicate_shard_cells_are_invalid_instead_of_arbitrarily_selected(self):
        case = self.manifest['pairs'][0]
        path = self.write('fixed', case, 'baseline', self.record('fixed', case, 'baseline', True, False))
        duplicate = self.results / 'second-shard' / 'model-a' / 'fixed' / case['id'] / 'baseline'
        duplicate.mkdir(parents=True)
        shutil.copyfile(path, duplicate / 'result.json')
        result = self.analyze()
        self.assertEqual(self.phase(result, 'fixed')['byArm']['baseline']['endpoints']['attack_success']['valid'], 0)
        invalid = [cell for cell in result['exceptions'] if cell['status'] == 'invalid']
        self.assertEqual(len(invalid), 1)
        self.assertEqual(len(invalid[0]['duplicateDirectories']), 2)

    def test_unplanned_development_cell_does_not_enter_evaluation(self):
        development = {'id': 'dev-00', 'userTask': 'user_task_2', 'injectionTask': 'injection_task_2'}
        self.write('fixed', development, 'baseline', self.record('fixed', development, 'baseline', True, True))
        result = self.analyze()
        self.assertEqual(result['cellStatusCounts'], {'missing': 30})
        self.assertEqual(len(result['unplannedCellDirectories']), 1)

    def test_clean_interventions_and_baseline_success_losses_are_distinct(self):
        self.manifest['cleanTasks'] = [{'id': f'clean-{i:02d}', 'userTask': f'user_task_{i}'} for i in range(3)]
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.digest = hashlib.sha256(self.manifest_path.read_bytes()).hexdigest()
        for index, case in enumerate(self.manifest['cleanTasks']):
            for arm in ('baseline', 'full-history'):
                utility = index != 2 if arm == 'baseline' else index == 2
                record = self.record('clean', case, arm, utility)
                denials = 2 if arm == 'full-history' and index == 0 else 0
                record.update(policy_denials=[{'decision': 'Review'}] * denials,
                              policy_event_count=0 if arm == 'baseline' else 3)
                self.write('clean', case, arm, record)
        clean = self.phase(self.analyze(), 'clean')
        intervention = clean['byArm']['full-history']['cleanTaskInterventions']
        self.assertEqual(intervention['completedCleanTasks'], 3)
        self.assertEqual(intervention['casesWithPolicyDenial'], 1)
        self.assertEqual(intervention['totalPolicyDenials'], 2)
        self.assertEqual(intervention['caseRateAmongCompleted'], 1 / 3)
        self.assertEqual(intervention['observedPolicyEventCount'], 9)
        loss = clean['cleanBaselineSuccessLosses']['full-history']
        self.assertEqual(loss['baselineSuccessCompletePairs'], 2)
        self.assertEqual(loss['baselineSuccessGateFailurePairs'], 2)
        self.assertEqual(loss['lossRateAmongBaselineSuccessCompletePairs'], 1)
        self.assertEqual(loss['baselineFailureGateSuccessPairs'], 1)
        self.assertEqual(loss['gainRateAmongBaselineFailureCompletePairs'], 1)
        self.assertEqual(clean['cleanBaselineSuccessLosses']['point-only']['completePairedTasks'], 0)

    def test_missing_clean_policy_diagnostics_do_not_invent_zero_denials(self):
        case = self.manifest['cleanTasks'][0]
        self.write('clean', case, 'full-history', self.record('clean', case, 'full-history', False))
        clean = self.phase(self.analyze(), 'clean')
        intervention = clean['byArm']['full-history']['cleanTaskInterventions']
        self.assertEqual(intervention['completedCleanTasks'], 1)
        self.assertEqual(intervention['completedTasksMissingPolicyDiagnostics'], 1)
        self.assertIsNone(intervention['caseRateAmongCompleted'])
        self.assertIsNone(intervention['totalPolicyDenials'])
        self.assertEqual(intervention['caseRateBoundsAmongCompleted'], [0, 1])
        self.assertEqual(clean['byArm']['full-history']['endpoints']['utility']['valid'], 1)


if __name__ == '__main__':
    unittest.main()
