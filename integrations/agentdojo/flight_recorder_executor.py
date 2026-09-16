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
    def __init__(self, path: Path, trusted_email_domains: Sequence[str] = ()) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Tool catalog must be a JSON object")
        self._rules: dict[str, dict[str, Any]] = raw
        self._trusted_email_domains = {domain.lower().lstrip("@") for domain in trusted_email_domains}

    @property
    def functions(self) -> set[str]:
        return set(self._rules)

    def action(self, function: str, session_id: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        rule = self._rules.get(function)
        if rule is None:
            raise KeyError(f"Unmapped AgentDojo tool: {function}")
        destination_trust = self._destination_trust(rule, arguments or {})
        action = {
            "id": str(uuid.uuid4()),
            "sessionId": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": "agentdojo",
            "operation": function,
            "resourceType": rule["resourceType"],
            "sensitivity": rule.get("sensitivity", "Internal"),
            "destinationTrust": destination_trust,
            "privilegeLevel": rule.get("privilegeLevel", 1),
            "inputProvenance": rule.get("inputProvenance", "TrustedTool"),
        }
        if destination_trust != rule.get("destinationTrust", "Trusted"):
            action["metadata"] = {"destinationTrustSource": "recipient-domain"}
        return action

    def _destination_trust(self, rule: dict[str, Any], arguments: dict[str, Any]) -> str:
        recipients = self._recipients(arguments)
        if not recipients or not self._trusted_email_domains:
            return rule.get("destinationTrust", "Trusted")
        domains = {recipient.rsplit("@", 1)[1].lower() for recipient in recipients}
        return "Trusted" if domains.issubset(self._trusted_email_domains) else "Untrusted"

    @staticmethod
    def _recipients(arguments: dict[str, Any]) -> list[str]:
        values: list[Any] = []
        for key in ("recipients", "participants"):
            value = arguments.get(key)
            values.extend(value if isinstance(value, list) else [value])
        return [value.strip() for value in values if isinstance(value, str) and "@" in value]


class FlightRecorderToolsExecutor(BasePipelineElement):
    """AgentDojo executor that asks the TypeScript gate before each tool effect."""

    def __init__(
        self,
        bridge: PolicyBridge,
        catalog: TrustedToolCatalog,
        session_id: str | None = None,
        review_policy: str = "approve",
        audit_path: Path | None = None,
        tool_output_formatter: Callable[[FunctionReturnType], str] = tool_result_to_str,
    ) -> None:
        if review_policy not in {"approve", "deny"}:
            raise ValueError("review_policy must be approve or deny")
        self.bridge = bridge
        self.catalog = catalog
        self.session_id = session_id
        self.review_policy = review_policy
        self.audit_path = audit_path
        self.output_formatter = tool_output_formatter
        if self.audit_path is not None:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            self.audit_path.write_text("", encoding="utf-8")

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
        session_id = extra_args.get("agent_flight_recorder_session_id") or self.session_id or str(uuid.uuid4())
        for tool_call in messages[-1]["tool_calls"]:
            try:
                action = self.catalog.action(tool_call.function, session_id, tool_call.args)
                assessment = self.bridge.request({"command": "assess", "action": action})["assessment"]
            except Exception as error:
                event = {"tool": tool_call.function, "decision": "Block", "executed": False, "error": str(error)}
                audit.append(event)
                self._emit(event)
                results.append(self._error_result(tool_call, str(error)))
                continue

            approved = assessment["decision"] != "Review" or self.review_policy == "approve"
            if assessment["decision"] == "Block" or not approved:
                reason = "; ".join(assessment.get("reasons", [])) or "Policy denied the tool call"
                event = {
                    "tool": tool_call.function,
                    "action": action,
                    "assessment": assessment,
                    "approved": approved,
                    "executed": False,
                }
                audit.append(event)
                self._emit(event)
                results.append(self._error_result(tool_call, reason))
                continue

            for key, value in tool_call.args.items():
                if isinstance(value, str) and is_string_list(value):
                    tool_call.args[key] = literal_eval(value)
            tool_result, error = runtime.run_function(env, tool_call.function, tool_call.args)
            if error is None:
                self.bridge.request({"command": "record", "action": action})
            event = {
                "tool": tool_call.function,
                "action": action,
                "assessment": assessment,
                "approved": approved,
                "executed": error is None,
                "error": error,
            }
            audit.append(event)
            self._emit(event)
            results.append(
                ChatToolResultMessage(
                    role="tool",
                    content=[text_content_block_from_string(self.output_formatter(tool_result))],
                    tool_call_id=tool_call.id,
                    tool_call=tool_call,
                    error=error,
                )
            )
        next_args = {
            **extra_args,
            "agent_flight_recorder": audit,
            "agent_flight_recorder_session_id": session_id,
        }
        return query, runtime, env, [*messages, *results], next_args

    def _emit(self, event: dict[str, Any]) -> None:
        if self.audit_path is None:
            return
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, separators=(",", ":"), default=str) + "\n")

    @staticmethod
    def _error_result(tool_call: Any, error: str) -> ChatToolResultMessage:
        return ChatToolResultMessage(
            role="tool",
            content=[text_content_block_from_string("")],
            tool_call_id=tool_call.id,
            tool_call=tool_call,
            error=error,
        )
