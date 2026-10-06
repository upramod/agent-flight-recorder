from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from adaptive_attack import CandidateGenerationError, CandidateResult
from run_validation_v3 import adaptive_episode, add_identity


CONFIG = {"slot": "model-a", "responseModel": "mock-target-model"}
ATTACKER = {"slot": "model-a", "responseModel": "mock-attacker-model"}
CASE = {"id": "case-001", "userTask": "user_task_0", "injectionTask": "injection_task_0"}
PAYLOAD = {"vector-a": "fixed attack", "vector-b": "fixed attack"}


def completed(success: bool, utility: bool = True, marker: str = "target") -> dict:
    return {
        "status": "completed", "attack_success": success, "utility": utility,
        "tool_messages": [{"marker": marker}],
        "policy_denials": [{"marker": marker, "decision": "Review"}],
    }


def fake_suite() -> SimpleNamespace:
    return SimpleNamespace(
        tools=[],
        get_user_task_by_id=lambda _: SimpleNamespace(PROMPT="Find the simulated event."),
        get_injection_task_by_id=lambda _: SimpleNamespace(GOAL="Cancel the simulated event."),
    )


def candidate(client, model, **kwargs) -> CandidateResult:
    number = kwargs["candidate_number"]
    return CandidateResult(
        injections={key: f"candidate {number}" for key in kwargs["allowed_vector_ids"]},
        audit={"status": "accepted", "candidate_number": number, "response_model": ATTACKER["responseModel"]},
    )


class AdaptiveEpisodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name)
        self.client = Mock()
        client_patch = patch("run_validation_v3.client_for", side_effect=lambda _: nullcontext(self.client))
        self.mock_client_for = client_patch.start()
        self.addCleanup(client_patch.stop)
        deployment_patch = patch("run_validation_v3.deployment_for", return_value="mock-attacker-deployment")
        deployment_patch.start()
        self.addCleanup(deployment_patch.stop)

    def episode(self, target, generator, *, arm="full-history", output=None, payload=None):
        return adaptive_episode(
            CONFIG, ATTACKER, arm, CASE, fake_suite(), PAYLOAD if payload is None else payload,
            self.output if output is None else output, "frozen-manifest-hash",
            attempts=5, target_fn=target, generator_fn=generator,
        )

    def test_first_attempt_success_stops_before_generation(self) -> None:
        target = Mock(return_value=completed(True, utility=False))
        generator = Mock(side_effect=candidate)
        result = self.episode(target, generator)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["attack_success"])
        self.assertFalse(result["first_attempt_utility"])
        self.assertEqual(len(result["attempts"]), 1)
        target.assert_called_once()
        generator.assert_not_called()
        self.mock_client_for.assert_not_called()
        self.assertEqual(target.call_args.args[4], PAYLOAD)
        self.assertFalse((self.output / "attempt-02").exists())

    def test_five_unsuccessful_targets_exhaust_budget_without_sixth_candidate(self) -> None:
        target = Mock(side_effect=[completed(False, utility=False) for _ in range(5)])
        observations = []

        def generate(client, model, **kwargs):
            observations.append(deepcopy(kwargs))
            return candidate(client, model, **kwargs)

        generator = Mock(side_effect=generate)
        result = self.episode(target, generator)
        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["attack_success"])
        self.assertEqual(target.call_count, 5)
        self.assertEqual(generator.call_count, 4)
        self.assertEqual([row["candidate_number"] for row in observations], [2, 3, 4, 5])
        self.assertEqual([len(row["previous_attempts"]) for row in observations], [1, 2, 3, 4])
        self.assertEqual(observations[0]["previous_attempts"][0]["injections"], PAYLOAD)
        self.assertEqual(observations[-1]["previous_attempts"][-1]["injections"], {
            key: "candidate 4" for key in PAYLOAD
        })
        self.assertEqual(len(result["attempts"]), 5)
        self.assertFalse((self.output / "attempt-06").exists())
        self.assertEqual(json.loads((self.output / "episode.json").read_text()), result)

    def test_success_after_failed_attempt_uses_feedback_then_stops(self) -> None:
        order = []
        requests = []

        def target(*args):
            order.append("target")
            return completed(len(order) > 1, marker=f"result-{len(order)}")

        def generate(client, model, **kwargs):
            order.append("generator")
            requests.append(deepcopy(kwargs))
            return candidate(client, model, **kwargs)

        result = self.episode(target, generate)
        self.assertEqual(order, ["target", "generator", "target"])
        self.assertTrue(result["attack_success"])
        self.assertEqual(len(result["attempts"]), 2)
        self.assertEqual(requests[0]["previous_attempts"][0]["tool_messages"], [{"marker": "result-1"}])
        self.assertFalse(requests[0]["previous_attempts"][0]["attack_success"])
        self.assertFalse((self.output / "attempt-03").exists())

    def test_target_error_leaves_episode_incomplete_not_attack_failure(self) -> None:
        for error_attempt in (1, 2):
            with self.subTest(error_attempt=error_attempt):
                target = Mock(side_effect=[completed(False)] * (error_attempt - 1) + [{
                    "status": "error", "utility": None, "attack_success": None,
                    "error": {"type": "RuntimeError", "message": "synthetic target failure"},
                }])
                generator = Mock(side_effect=candidate)
                result = self.episode(target, generator, output=self.output / str(error_attempt))
                self.assertEqual(result["status"], "error")
                self.assertIsNone(result["attack_success"])
                self.assertEqual(result["error"]["stage"], "target")
                self.assertEqual(result["error"]["type"], "TargetExecutionError")
                self.assertEqual(target.call_count, error_attempt)
                self.assertEqual(generator.call_count, error_attempt - 1)
                self.assertEqual(len(result["attempts"]), error_attempt)

    def test_generation_error_leaves_episode_incomplete_without_another_target(self) -> None:
        target = Mock(return_value=completed(False))
        audit = {"status": "rejected", "candidate_number": 2, "response_content": "invalid JSON"}
        generator = Mock(side_effect=CandidateGenerationError("invalid payload", audit))
        result = self.episode(target, generator)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["attack_success"])
        self.assertEqual(result["error"]["stage"], "attacker_generation")
        self.assertEqual(len(result["attempts"]), 1)
        target.assert_called_once()
        generator.assert_called_once()
        self.assertFalse((self.output / "attempt-02" / "result.json").exists())
        audit_path = self.output / "attacker-generation-02.json"
        self.assertEqual(json.loads(audit_path.read_text()), audit)

    def test_feedback_is_isolated_between_arms_and_fixed_payload_stays_unchanged(self) -> None:
        observed = {}
        initial = deepcopy(PAYLOAD)
        for arm in ("point-only", "full-history"):
            target = Mock(side_effect=[completed(False, marker=arm), completed(True, marker=arm)])

            def generate(client, model, **kwargs):
                observed[kwargs["selected_arm"]] = deepcopy(kwargs)
                return candidate(client, model, **kwargs)

            result = self.episode(target, generate, arm=arm, output=self.output / arm, payload=initial)
            self.assertTrue(result["attack_success"])
            self.assertEqual(target.call_args_list[0].args[4], PAYLOAD)
        self.assertEqual(initial, PAYLOAD)
        for arm, request in observed.items():
            self.assertEqual(len(request["previous_attempts"]), 1)
            self.assertEqual(request["previous_attempts"][0]["tool_messages"], [{"marker": arm}])
            self.assertEqual(request["previous_attempts"][0]["injections"], PAYLOAD)
            self.assertEqual(set(request["allowed_vector_ids"]), set(PAYLOAD))
        self.assertIsNot(observed["point-only"]["previous_attempts"], observed["full-history"]["previous_attempts"])

    def test_changed_attacker_model_is_an_incomplete_episode(self) -> None:
        target = Mock(return_value=completed(False))
        generator = Mock(return_value=CandidateResult(
            injections=dict(PAYLOAD),
            audit={"status": "accepted", "response_model": "unexpected-attacker-model"},
        ))
        result = self.episode(target, generator)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["attack_success"])
        self.assertEqual(result["error"], {"type": "AttackerIdentityDrift", "stage": "attacker_generation"})
        target.assert_called_once()
        self.assertFalse((self.output / "attempt-02" / "result.json").exists())

    def test_clean_case_drops_injection_task_from_identity(self) -> None:
        result = add_identity(completed(False), CASE, "model-a", "baseline", "hash", "clean")
        self.assertIsNone(result["injectionTask"])
        self.assertEqual(result["userTask"], CASE["userTask"])


if __name__ == "__main__":
    unittest.main()
