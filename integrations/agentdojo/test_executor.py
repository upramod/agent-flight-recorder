from __future__ import annotations

import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from agentdojo.attacks.base_attacks import get_model_name_from_pipeline
from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
from agentdojo.logging import Logger, OutputLogger
from agentdojo.task_suite.load_suites import get_suite

from flight_recorder_executor import FlightRecorderToolsExecutor, PolicyBridge, TrustedToolCatalog
from run_benchmark import pipeline_name, with_output_logger
from summarize_pilot import parse_console, summarize


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "integrations" / "agentdojo" / "workspace-policy.json"


class ExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bridge = PolicyBridge(ROOT)
        self.runtime = FunctionsRuntime()
        self.effects: list[str] = []

        @self.runtime.register_function
        def search_files(query: str) -> str:
            """Search files.

            :param query: Search query.
            """
            self.effects.append(query)
            return "synthetic result"

        self.executor = FlightRecorderToolsExecutor(
            self.bridge,
            TrustedToolCatalog(CATALOG),
            session_id="python-smoke",
        )

    def tearDown(self) -> None:
        self.bridge.close()

    @staticmethod
    def messages(function: str):
        return [{
            "role": "assistant",
            "content": None,
            "tool_calls": [FunctionCall(function=function, args={"query": "report"}, id="call-1")],
        }]

    def test_mapped_tool_executes_and_is_recorded(self) -> None:
        _, _, _, messages, extra = self.executor.query("query", self.runtime, messages=self.messages("search_files"))
        self.assertEqual(self.effects, ["report"])
        self.assertIsNone(messages[-1]["error"])
        self.assertTrue(extra["agent_flight_recorder"][0]["executed"])
        history = self.bridge.request({"command": "history", "sessionId": "python-smoke"})["history"]
        self.assertEqual(len(history), 1)

    def test_unmapped_tool_fails_closed_without_effect(self) -> None:
        _, _, _, messages, extra = self.executor.query("query", self.runtime, messages=self.messages("unknown_tool"))
        self.assertEqual(self.effects, [])
        self.assertIn("Unmapped AgentDojo tool", messages[-1]["error"])
        self.assertFalse(extra["agent_flight_recorder"][0]["executed"])

    def test_policy_sidecar_records_decision_and_execution(self) -> None:
        with TemporaryDirectory() as directory:
            audit_path = Path(directory) / "policy.jsonl"
            executor = FlightRecorderToolsExecutor(
                self.bridge,
                TrustedToolCatalog(CATALOG),
                session_id="sidecar-test",
                audit_path=audit_path,
            )
            executor.query("query", self.runtime, messages=self.messages("search_files"))
            events = [json.loads(line) for line in audit_path.read_text().splitlines()]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["assessment"]["decision"], "Allow")
            self.assertTrue(events[0]["executed"])

    def test_catalog_exactly_covers_pinned_workspace_suite(self) -> None:
        suite = get_suite("v1.2.2", "workspace")
        runtime_names = {function.name for function in suite.tools}
        catalog_names = TrustedToolCatalog(CATALOG).functions
        self.assertEqual(catalog_names, runtime_names)

    def test_recipient_domains_define_the_outbound_trust_boundary(self) -> None:
        catalog = TrustedToolCatalog(CATALOG, ["bluesparrowtech.com"])
        internal = catalog.action(
            "send_email",
            "domain-boundary",
            {"recipients": ["teammate@bluesparrowtech.com"]},
        )
        external = catalog.action(
            "send_email",
            "domain-boundary",
            {"recipients": ["attacker@outside.invalid"]},
        )
        self.assertEqual(internal["destinationTrust"], "Trusted")
        self.assertEqual(internal["metadata"]["destinationTrustSource"], "recipient-domain")
        self.assertEqual(external["destinationTrust"], "Untrusted")
        self.assertEqual(external["metadata"]["destinationTrustSource"], "recipient-domain")

    def test_external_email_after_external_input_is_blocked(self) -> None:
        catalog = TrustedToolCatalog(CATALOG, ["bluesparrowtech.com"])
        session_id = "external-email-block"
        source = catalog.action("search_calendar_events", session_id, {"query": "meeting"})
        self.bridge.request({"command": "record", "action": source})
        email = catalog.action(
            "send_email",
            session_id,
            {"recipients": ["attacker@outside.invalid"], "subject": "report", "body": "data"},
        )
        assessment = self.bridge.request({"command": "assess", "action": email})["assessment"]
        self.assertEqual(assessment["decision"], "Block")
        self.assertGreaterEqual(assessment["score"], 70)

    def test_independent_queries_receive_isolated_sessions(self) -> None:
        executor = FlightRecorderToolsExecutor(self.bridge, TrustedToolCatalog(CATALOG))
        first = executor.query("first", self.runtime, messages=self.messages("search_files"))[4]
        second = executor.query("second", self.runtime, messages=self.messages("search_files"))[4]
        self.assertNotEqual(
            first["agent_flight_recorder_session_id"],
            second["agent_flight_recorder_session_id"],
        )
        self.assertEqual(
            len(self.bridge.request({
                "command": "history",
                "sessionId": first["agent_flight_recorder_session_id"],
            })["history"]),
            1,
        )

    def test_benchmark_pipeline_name_is_accepted_by_agentdojo_attacks(self) -> None:
        name = pipeline_name("baseline", "approve", "gpt-4.1-mini-deployment")
        self.assertEqual(get_model_name_from_pipeline(SimpleNamespace(name=name)), "GPT-4")
        self.assertIn("gpt-4.1-mini-deployment", name)

    def test_benchmark_runs_inside_agentdojo_output_logger(self) -> None:
        with TemporaryDirectory() as directory:
            def inspect_logger() -> str:
                logger = Logger.get()
                self.assertIsInstance(logger, OutputLogger)
                return logger.logdir

            self.assertEqual(with_output_logger(Path(directory), inspect_logger), directory)

    def test_pilot_summary_rejects_incomplete_output(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            console = root / "case-0" / "baseline-console.txt"
            console.parent.mkdir(parents=True)
            console.write_text("utility=1/1\n")
            with self.assertRaises(ValueError):
                parse_console(console)

    def test_pilot_summary_reads_one_row_per_mode(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            case = root / "case-0"
            case.mkdir()
            (case / "baseline-console.txt").write_text("utility=1/1\nsecurity=0/1\n")
            (case / "flight-recorder-console.txt").write_text("utility=1/1\nsecurity=1/1\n")
            policy_dir = case / "flight-recorder"
            policy_dir.mkdir()
            (policy_dir / "flight-recorder-policy.jsonl").write_text(
                '{"assessment":{"decision":"Review"},"executed":false}\n'
                '{"assessment":{"decision":"Block"},"executed":false}\n'
            )
            rows = summarize(root)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["case"], "case-0")
            self.assertEqual(rows[0]["mode"], "baseline")
            self.assertEqual(rows[1]["security_passed"], 1)
            self.assertEqual(rows[1]["review"], 1)
            self.assertEqual(rows[1]["block"], 1)
            self.assertEqual(rows[1]["denied"], 2)


if __name__ == "__main__":
    unittest.main()
