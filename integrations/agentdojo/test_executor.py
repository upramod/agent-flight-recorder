from __future__ import annotations

import unittest
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock

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

    def test_bridge_close_releases_all_pipes_and_is_idempotent(self) -> None:
        self.bridge.close()
        self.bridge.close()
        self.assertIsNotNone(self.bridge._process.poll())
        for stream in (self.bridge._process.stdin, self.bridge._process.stdout, self.bridge._process.stderr):
            self.assertTrue(stream.closed)

    def test_bridge_close_kills_on_timeout_and_closes_remaining_pipes(self) -> None:
        bridge = PolicyBridge.__new__(PolicyBridge)
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("node", 5), 0]
        process.stdin.close.side_effect = BrokenPipeError("child pipe closed")
        bridge._process = process
        bridge.close()
        process.terminate.assert_called_once_with()
        process.kill.assert_called_once_with()
        self.assertEqual([call.kwargs for call in process.wait.call_args_list], [{"timeout": 5}, {"timeout": 5}])
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close.assert_called_once_with()

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
        internal = catalog.action("send_email", "domain-boundary", {"recipients": ["teammate@bluesparrowtech.com"]})
        external = catalog.action("send_email", "domain-boundary", {"recipients": ["attacker@outside.invalid"]})
        self.assertEqual(internal["destinationTrust"], "Trusted")
        self.assertEqual(internal["metadata"]["destinationTrustSource"], "recipient-domain")
        self.assertEqual(external["destinationTrust"], "Untrusted")
        self.assertEqual(external["metadata"]["destinationTrustSource"], "recipient-domain")

    def test_all_pinned_outbound_recipient_fields_affect_trust(self) -> None:
        tools = {tool.name: tool for tool in get_suite("v1.2.2", "workspace").tools}
        catalog = TrustedToolCatalog(CATALOG, ["bluesparrowtech.com"])
        internal = "teammate@bluesparrowtech.com"
        external = "outside@outside.invalid"
        cases = [
            ("send_email", {"recipients": [external], "subject": "report", "body": "text"}),
            ("send_email", {"recipients": [internal], "subject": "report", "body": "text", "cc": [external]}),
            ("send_email", {"recipients": [internal], "subject": "report", "body": "text", "bcc": [external]}),
            ("create_calendar_event", {"title": "meeting", "start_time": "2024-05-30 10:00",
                                       "end_time": "2024-05-30 11:00", "participants": [internal, external]}),
            ("add_calendar_event_participants", {"event_id": "1", "participants": [internal, external]}),
            ("share_file", {"file_id": "1", "email": external, "permission": "r"}),
        ]
        for function, arguments in cases:
            with self.subTest(function=function, arguments=arguments):
                # Validate fixtures against AgentDojo's actual pinned input schemas.
                normalized = tools[function].parameters.model_validate(arguments).model_dump()
                action = catalog.action(function, "outbound-fields", normalized)
                self.assertEqual(action["destinationTrust"], "Untrusted")

    def test_cc_bcc_and_file_sharing_are_blocked_after_external_input(self) -> None:
        catalog = TrustedToolCatalog(CATALOG, ["bluesparrowtech.com"])
        session_id = "all-destinations"
        self.bridge.request({"command": "record", "action": catalog.action("search_calendar_events", session_id)})
        calls = [
            ("send_email", {"recipients": ["teammate@bluesparrowtech.com"], "cc": ["outside@outside.invalid"]}),
            ("send_email", {"recipients": ["teammate@bluesparrowtech.com"], "bcc": ["outside@outside.invalid"]}),
            ("share_file", {"email": "outside@outside.invalid"}),
        ]
        for function, arguments in calls:
            with self.subTest(function=function, arguments=arguments):
                action = catalog.action(function, session_id, arguments)
                assessment = self.bridge.request({"command": "assess", "action": action})["assessment"]
                self.assertEqual(assessment["decision"], "Block")
                self.assertEqual(assessment["score"], 80)

    def test_destination_defaults_and_read_arguments_keep_existing_meaning(self) -> None:
        catalog = TrustedToolCatalog(CATALOG, ["bluesparrowtech.com"])
        without_domains = TrustedToolCatalog(CATALOG)
        for function, expected in (("send_email", "Unknown"), ("share_file", "Unknown"),
                                   ("create_calendar_event", "Trusted"),
                                   ("add_calendar_event_participants", "Unknown")):
            with self.subTest(function=function):
                self.assertEqual(catalog.action(function, "defaults", {})["destinationTrust"], expected)
                self.assertEqual(catalog.action(function, "defaults", {"participants": None})["destinationTrust"], expected)
                self.assertEqual(without_domains.action(function, "defaults", {
                    "recipients": ["outside@outside.invalid"], "participants": ["outside@outside.invalid"],
                    "email": "outside@outside.invalid",
                })["destinationTrust"], expected)
        read = catalog.action("search_contacts_by_email", "defaults", {"email": "outside@outside.invalid"})
        self.assertEqual(read["destinationTrust"], "Trusted")
        self.assertNotIn("metadata", read)

    def test_recipient_domain_matching_is_exact_and_case_insensitive(self) -> None:
        catalog = TrustedToolCatalog(CATALOG, ["bluesparrowtech.com"])
        for email, expected in (("Teammate@BLUESPARROWTECH.COM", "Trusted"),
                                ("person@sub.bluesparrowtech.com", "Untrusted"),
                                ("person@bluesparrowtech.com.outside.invalid", "Untrusted")):
            with self.subTest(email=email):
                self.assertEqual(catalog.action("share_file", "domains", {"email": email})["destinationTrust"], expected)

    def test_invalid_catalog_security_fields_fail_before_use(self) -> None:
        valid_rule = json.loads(CATALOG.read_text())["send_email"]
        invalid_values = {
            "resourceType": [None, "", "   ", 4],
            "sensitivity": [None, "Secret", [], 1],
            "destinationTrust": [None, "trusted", {}, 1],
            "inputProvenance": [None, "Untrusted", [], 1],
            "privilegeLevel": [None, True, 0, -1, 1.5, "4", 2**53],
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            for field, values in invalid_values.items():
                for value in values:
                    with self.subTest(field=field, value=value):
                        path.write_text(json.dumps({"send_email": {**valid_rule, field: value}}))
                        with self.assertRaises(ValueError):
                            TrustedToolCatalog(path, ["bluesparrowtech.com"])
            for rule in (None, [], {}, {**valid_rule, "resourceType": ""}):
                with self.subTest(rule=rule):
                    path.write_text(json.dumps({"send_email": rule}))
                    with self.assertRaises(ValueError):
                        TrustedToolCatalog(path)

    def test_omitted_catalog_defaults_are_materialized_and_validated(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps({"custom_read": {"resourceType": "document"}}))
            action = TrustedToolCatalog(path).action("custom_read", "valid-session")
        self.assertEqual(action["sensitivity"], "Internal")
        self.assertEqual(action["destinationTrust"], "Trusted")
        self.assertEqual(action["inputProvenance"], "TrustedTool")
        self.assertEqual(action["privilegeLevel"], 1)

    def test_incomplete_action_cannot_reach_bridge_or_runtime(self) -> None:
        valid = TrustedToolCatalog(CATALOG).action("search_files", "valid-session")
        for field in ("id", "sessionId", "timestamp", "tool", "operation", "resourceType", "sensitivity",
                      "destinationTrust", "inputProvenance", "privilegeLevel"):
            with self.subTest(field=field):
                invalid = dict(valid)
                del invalid[field]
                bridge = Mock(spec=PolicyBridge)
                catalog = Mock(spec=TrustedToolCatalog)
                catalog.action.return_value = invalid
                executor = FlightRecorderToolsExecutor(bridge, catalog)
                *_, extra = executor.query("query", self.runtime, messages=self.messages("search_files"))
                bridge.request.assert_not_called()
                self.assertEqual(self.effects, [])
                event = extra["agent_flight_recorder"][0]
                self.assertEqual(event["decision"], "Block")
                self.assertFalse(event["executed"])

    def test_supplied_invalid_sessions_fail_closed_instead_of_resetting_history(self) -> None:
        catalog = TrustedToolCatalog(CATALOG)
        for session_id in (None, "", "   ", False, 0, [], {}):
            with self.subTest(session_id=session_id):
                bridge = Mock(spec=PolicyBridge)
                executor = FlightRecorderToolsExecutor(bridge, catalog, session_id="fallback-must-not-be-used")
                *_, extra = executor.query("query", self.runtime, messages=self.messages("search_files"),
                                           extra_args={"agent_flight_recorder_session_id": session_id})
                bridge.request.assert_not_called()
                self.assertEqual(self.effects, [])
                self.assertIn("sessionId", extra["agent_flight_recorder"][0]["error"])

    def test_point_only_mode_is_forwarded_and_successful_execution_is_recorded(self) -> None:
        bridge = Mock(spec=PolicyBridge)
        bridge.request.side_effect = [
            {"assessment": {"decision": "Allow", "score": 20, "reasons": [], "historyLength": 0}},
            {"recorded": True},
        ]
        executor = FlightRecorderToolsExecutor(bridge, TrustedToolCatalog(CATALOG), policy_mode="point-only")
        *_, extra = executor.query("query", self.runtime, messages=self.messages("search_files"))
        assess, record = [call.args[0] for call in bridge.request.call_args_list]
        self.assertEqual(assess["command"], "assess")
        self.assertEqual(assess["policyMode"], "point-only")
        self.assertEqual(record, {"command": "record", "action": assess["action"]})
        self.assertEqual(extra["agent_flight_recorder"][0]["policyMode"], "point-only")
        self.assertEqual(self.effects, ["report"])
        with self.assertRaises(ValueError):
            FlightRecorderToolsExecutor(bridge, TrustedToolCatalog(CATALOG), policy_mode="invalid")

    def test_point_only_assessment_ignores_history_without_losing_execution_records(self) -> None:
        @self.runtime.register_function
        def get_unread_emails() -> str:
            """Read unread email messages."""
            self.effects.append("read-emails")
            return "synthetic email"

        for mode, decision, history_length, executed_count in (
            ("full-history", "Review", 1, 1),
            ("point-only", "Allow", 0, 2),
        ):
            with self.subTest(mode=mode):
                session_id = f"mode-{mode}"
                executor = FlightRecorderToolsExecutor(
                    self.bridge, TrustedToolCatalog(CATALOG), session_id=session_id,
                    review_policy="deny", policy_mode=mode,
                )
                extra = {}
                for index in range(2):
                    messages = [{"role": "assistant", "content": None, "tool_calls": [
                        FunctionCall(function="get_unread_emails", args={}, id=f"read-{index}")
                    ]}]
                    *_, extra = executor.query("query", self.runtime, messages=messages, extra_args=extra)
                event = extra["agent_flight_recorder"][-1]
                self.assertEqual(event["policyMode"], mode)
                self.assertEqual(event["assessment"]["decision"], decision)
                self.assertEqual(event["assessment"]["historyLength"], history_length)
                history = self.bridge.request({"command": "history", "sessionId": session_id})["history"]
                self.assertEqual(len(history), executed_count)

    def test_external_email_after_external_input_is_blocked(self) -> None:
        catalog = TrustedToolCatalog(CATALOG, ["bluesparrowtech.com"])
        session_id = "external-email-block"
        source = catalog.action("search_calendar_events", session_id, {"query": "meeting"})
        self.bridge.request({"command": "record", "action": source})
        email = catalog.action("send_email", session_id, {"recipients": ["attacker@outside.invalid"], "subject": "report", "body": "data"})
        assessment = self.bridge.request({"command": "assess", "action": email})["assessment"]
        self.assertEqual(assessment["decision"], "Block")
        self.assertGreaterEqual(assessment["score"], 70)

    def test_calendar_recipient_metadata_uses_normalized_arguments(self) -> None:
        @self.runtime.register_function
        def create_calendar_event(participants: list[str]) -> str:
            """Create a calendar event.

            :param participants: Event participant addresses.
            """
            self.effects.extend(participants)
            return "created"

        catalog = TrustedToolCatalog(CATALOG, ["bluesparrowtech.com"])
        representations = [
            ["outside@outside.invalid"],
            "['outside@outside.invalid']",
            "['outside@outside.invalid'] #@bluesparrowtech.com",
        ]
        for index, participants in enumerate(representations):
            with self.subTest(participants=participants):
                session_id = f"normalized-calendar-{index}"
                source = catalog.action("search_calendar_events", session_id, {"query": "meeting"})
                self.bridge.request({"command": "record", "action": source})
                executor = FlightRecorderToolsExecutor(
                    self.bridge, catalog, session_id=session_id, review_policy="deny"
                )
                messages = [{
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [FunctionCall(
                        function="create_calendar_event",
                        args={"participants": participants},
                        id=f"calendar-{index}",
                    )],
                }]
                *_, extra = executor.query("query", self.runtime, messages=messages)
                event = extra["agent_flight_recorder"][0]
                self.assertEqual(event["action"]["destinationTrust"], "Untrusted")
                self.assertEqual(event["assessment"]["decision"], "Review")
                self.assertFalse(event["executed"])
                self.assertEqual(self.effects, [])
                self.assertEqual(messages[0]["tool_calls"][0].args["participants"], participants)

    def test_calendar_execution_receives_the_assessed_normalized_arguments(self) -> None:
        @self.runtime.register_function
        def create_calendar_event(participants: list[str]) -> str:
            """Create a calendar event.

            :param participants: Event participant addresses.
            """
            self.effects.extend(participants)
            return "created"

        catalog = TrustedToolCatalog(CATALOG, ["bluesparrowtech.com"])
        executor = FlightRecorderToolsExecutor(
            self.bridge, catalog, session_id="normalized-approved", review_policy="deny"
        )
        participants = "['teammate@bluesparrowtech.com']"
        messages = [{
            "role": "assistant",
            "content": None,
            "tool_calls": [FunctionCall(
                function="create_calendar_event", args={"participants": participants}, id="calendar-safe"
            )],
        }]
        *_, extra = executor.query("query", self.runtime, messages=messages)
        event = extra["agent_flight_recorder"][0]
        self.assertEqual(event["action"]["destinationTrust"], "Trusted")
        self.assertTrue(event["executed"])
        self.assertEqual(self.effects, ["teammate@bluesparrowtech.com"])
        self.assertEqual(messages[0]["tool_calls"][0].args["participants"], participants)

    def test_independent_queries_receive_isolated_sessions(self) -> None:
        executor = FlightRecorderToolsExecutor(self.bridge, TrustedToolCatalog(CATALOG))
        first = executor.query("first", self.runtime, messages=self.messages("search_files"))[4]
        second = executor.query("second", self.runtime, messages=self.messages("search_files"))[4]
        self.assertNotEqual(first["agent_flight_recorder_session_id"], second["agent_flight_recorder_session_id"])
        self.assertEqual(len(self.bridge.request({"command": "history", "sessionId": first["agent_flight_recorder_session_id"]})["history"]), 1)

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
            (case / "baseline-console.txt").write_text("utility=1/1\nattack_success=0/1\nattack_resisted=1/1\n")
            (case / "flight-recorder-console.txt").write_text("utility=1/1\nattack_success=1/1\nattack_resisted=0/1\n")
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
            self.assertEqual(rows[1]["attack_success"], 1)
            self.assertEqual(rows[1]["attack_resisted"], 0)
            self.assertEqual(rows[1]["review"], 1)
            self.assertEqual(rows[1]["block"], 1)
            self.assertEqual(rows[1]["denied"], 2)


if __name__ == "__main__":
    unittest.main()
