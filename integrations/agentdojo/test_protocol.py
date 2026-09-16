from __future__ import annotations

import json
import unittest
from pathlib import Path

from agentdojo.task_suite.load_suites import get_suite

from analyze_paired import exact_mcnemar
from run_manifest import pair_set

ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC = ROOT / "integrations" / "agentdojo" / "benchmark-manifest.json"
HOLDOUT = ROOT / "integrations" / "agentdojo" / "holdout-manifest.json"


class ProtocolTests(unittest.TestCase):
    def test_holdout_is_thirty_valid_nonoverlapping_pairs(self) -> None:
        diagnostic = json.loads(DIAGNOSTIC.read_text(encoding="utf-8"))
        holdout = json.loads(HOLDOUT.read_text(encoding="utf-8"))
        self.assertEqual(len(holdout["pairs"]), 30)
        self.assertEqual(pair_set(diagnostic) & pair_set(holdout), set())

        suite = get_suite(holdout["benchmarkVersion"], holdout["suite"])
        valid_users = set(suite.user_tasks)
        valid_injections = set(suite.injection_tasks)
        for pair in holdout["pairs"]:
            self.assertIn(pair["userTask"], valid_users)
            self.assertIn(pair["injectionTask"], valid_injections)

    def test_holdout_uses_injection_objectives_absent_from_diagnostic(self) -> None:
        diagnostic = json.loads(DIAGNOSTIC.read_text(encoding="utf-8"))
        holdout = json.loads(HOLDOUT.read_text(encoding="utf-8"))
        diagnostic_injections = {pair["injectionTask"] for pair in diagnostic["pairs"]}
        holdout_injections = {pair["injectionTask"] for pair in holdout["pairs"]}
        self.assertEqual(
            holdout_injections,
            {"injection_task_10", "injection_task_11", "injection_task_12", "injection_task_13"},
        )
        self.assertTrue(holdout_injections.isdisjoint(diagnostic_injections))

    def test_exact_mcnemar_known_value(self) -> None:
        self.assertAlmostEqual(exact_mcnemar(10, 0), 0.001953125)
        self.assertEqual(exact_mcnemar(0, 0), 1.0)


if __name__ == "__main__":
    unittest.main()
