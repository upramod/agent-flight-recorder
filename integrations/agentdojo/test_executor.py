from __future__ import annotations

import unittest
from pathlib import Path

from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite

from flight_recorder_executor import FlightRecorderToolsExecutor, PolicyBridge, TrustedToolCatalog


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

    def test_catalog_exactly_covers_pinned_workspace_suite(self) -> None:
        suite = get_suite("v1.2.2", "workspace")
        runtime_names = {function.name for function in suite.tools}
        catalog_names = TrustedToolCatalog(CATALOG).functions
        self.assertEqual(catalog_names, runtime_names)


if __name__ == "__main__":
    unittest.main()
