from __future__ import annotations

import json
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.tool_execution import is_string_list, tool_result_to_str
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionReturnType, FunctionsRuntime
from agentdojo.types import ChatMessage, ChatToolResultMessage, text_content_block_from_string
from ast import literal_eval


class PolicyBridge:
    def __init__(self, repository_root: Path) -> None:
        bridge = repository_root / "dist" / "policyBridge.js"
        if not bridge.exists():
            raise FileNotFoundError("Run npm run build before starting AgentDojo")
        self._process = subprocess.Popen(
            ["node", str(bridge)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._lock = threading.Lock()

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._process.poll() is not None:
                raise RuntimeError("Policy bridge stopped")
            assert self._process.stdin is not None
            assert self._process.stdout is not None
            self._process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
            self._process.stdin.flush()
            line = self._process.stdout.readline()
        if not line:
            raise RuntimeError("Policy bridge returned no response")
        response = json.loads(line)
        if not response.get("ok"):
            raise RuntimeError(response.get("error", "Policy bridge failed"))
        return response

    def close(self) -> None:
        if self._process.poll() is None:
            self._process.terminate()
            self._process.wait(timeout=5)


class TrustedToolCatalog:
    def __init__(self, path: Path) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Tool catalog must be a JSON object")
        self._rules: dict[str, dict[str, Any]] = raw

    def action(self, function: str, session_id: str) -> dict[str, Any]:
        rule = self._rules.get(function)
        if rule is None:
            raise KeyError(f"Unmapped AgentDojo tool: {function}")
        return {
            "id": str(uuid.uuid4()),
            "sessionId": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": "agentdojo",
            "operation": function,
            "resourceType": rule["resourceType"],
            "sensitivity": rule.get("sensitivity", "Internal"),
            "destinationTrust": rule.get("destinationTrust", "Trusted"),
            "privilegeLevel": rule.get("privilegeLevel", 1),
            "inputProvenance": rule.get("inputProvenance", "TrustedTool"),
        }


class FlightRecorderToolsExecutor(BasePipelineElement):
    """AgentDojo executor that asks the TypeScript gate before each tool effect."""

    def __init__(
        self,
        bridge: PolicyBridge,
        catalog: TrustedToolCatalog,
        session_id: str,
        review_policy: str = "approve",
        tool_output_formatter: Callable[[FunctionReturnType], str] = tool_result_to_str,
    ) -> None:
        if review_policy not in {"approve", "deny"}:
            raise ValueError("review_policy must be approve or deny")
        self.bridge = bridge
        self.catalog = catalog
        self.session_id = session_id
        self.review_policy = review_policy
        self.output_formatter = tool_output_formatter

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        if not messages or messages[-1]["role"] != "assistant" or not messages[-1]["tool_calls"]:
            return query, runtime, env, messages, extra_args

        results: list[ChatToolResultMessage] = []
        audit = list(extra_args.get("agent_flight_recorder", []))
        for tool_call in messages[-1]["tool_calls"]:
            try:
                action = self.catalog.action(tool_call.function, self.session_id)
                assessment = self.bridge.request({"command": "assess", "action": action})["assessment"]
            except Exception as error:
                audit.append({"tool": tool_call.function, "decision": "Block", "executed": False, "error": str(error)})
                results.append(self._error_result(tool_call, str(error)))
                continue

            approved = assessment["decision"] != "Review" or self.review_policy == "approve"
            if assessment["decision"] == "Block" or not approved:
                reason = "; ".join(assessment.get("reasons", [])) or "Policy denied the tool call"
                audit.append({"tool": tool_call.function, "assessment": assessment, "executed": False})
                results.append(self._error_result(tool_call, reason))
                continue

            for key, value in tool_call.args.items():
                if isinstance(value, str) and is_string_list(value):
                    tool_call.args[key] = literal_eval(value)
            tool_result, error = runtime.run_function(env, tool_call.function, tool_call.args)
            if error is None:
                self.bridge.request({"command": "record", "action": action})
            audit.append({"tool": tool_call.function, "assessment": assessment, "executed": error is None})
            results.append(
                ChatToolResultMessage(
                    role="tool",
                    content=[text_content_block_from_string(self.output_formatter(tool_result))],
                    tool_call_id=tool_call.id,
                    tool_call=tool_call,
                    error=error,
                )
            )
        next_args = {**extra_args, "agent_flight_recorder": audit}
        return query, runtime, env, [*messages, *results], next_args

    @staticmethod
    def _error_result(tool_call: Any, error: str) -> ChatToolResultMessage:
        return ChatToolResultMessage(
            role="tool",
            content=[text_content_block_from_string("")],
            tool_call_id=tool_call.id,
            tool_call=tool_call,
            error=error,
        )
