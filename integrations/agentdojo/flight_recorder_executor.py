from __future__ import annotations

import json
import subprocess
import threading
import uuid
from copy import deepcopy
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
        try:
            if self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=5)
        finally:
            for stream in (self._process.stdin, self._process.stdout, self._process.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        # A broken child pipe must not prevent closing the others.
                        pass


class TrustedToolCatalog:
    # These are outbound arguments in the pinned workspace tool schemas.
    # An email-shaped argument to a read/search tool is not a destination.
    RECIPIENT_FIELDS = {
        "send_email": ("recipients", "cc", "bcc"),
        "create_calendar_event": ("participants",),
        "add_calendar_event_participants": ("participants",),
        "share_file": ("email",),
    }
    SECURITY_ENUMS = {
        "sensitivity": {"Public", "Internal", "Confidential", "Restricted"},
        "destinationTrust": {"Trusted", "Unknown", "Untrusted"},
        "inputProvenance": {"System", "User", "TrustedTool", "UntrustedDocument", "External"},
    }

    def __init__(self, path: Path, trusted_email_domains: Sequence[str] = ()) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Tool catalog must be a JSON object")
        self._rules: dict[str, dict[str, Any]] = raw
        self._trusted_email_domains = {domain.lower().lstrip("@") for domain in trusted_email_domains}
        # Validate every materialized rule before a benchmark can make model calls.
        for function in self._rules:
            self.action(function, "catalog-validation")

    @property
    def functions(self) -> set[str]:
        return set(self._rules)

    def action(self, function: str, session_id: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require_string(function, "operation")
        self._require_string(session_id, "sessionId")
        if function not in self._rules:
            raise KeyError(f"Unmapped AgentDojo tool: {function}")
        rule = self._rules[function]
        if not isinstance(rule, dict):
            raise ValueError(f"Tool catalog rule must be an object: {function}")
        if arguments is not None and not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object")
        action = {
            "id": str(uuid.uuid4()),
            "sessionId": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": "agentdojo",
            "operation": function,
            "resourceType": rule.get("resourceType"),
            "sensitivity": rule.get("sensitivity", "Internal"),
            "destinationTrust": rule.get("destinationTrust", "Trusted"),
            "privilegeLevel": rule.get("privilegeLevel", 1),
            "inputProvenance": rule.get("inputProvenance", "TrustedTool"),
        }
        # Keep the original omission defaults, but never let an invalid explicit
        # value be hidden by a recipient-derived replacement.
        self.validate_action(action)
        destination_trust = self._destination_trust(function, rule, arguments or {})
        action["destinationTrust"] = destination_trust
        if destination_trust != rule.get("destinationTrust", "Trusted"):
            action["metadata"] = {"destinationTrustSource": "recipient-domain"}
        return action

    @staticmethod
    def _require_string(value: Any, field: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Action {field} must be a nonempty string")

    @classmethod
    def validate_action(cls, action: dict[str, Any]) -> None:
        if not isinstance(action, dict):
            raise ValueError("Action must be an object")
        for field in ("id", "sessionId", "timestamp", "tool", "operation", "resourceType"):
            cls._require_string(action.get(field), field)
        for field, allowed in cls.SECURITY_ENUMS.items():
            value = action.get(field)
            if not isinstance(value, str) or value not in allowed:
                raise ValueError(f"Invalid action {field}")
        privilege = action.get("privilegeLevel")
        # The engine defines >=4 as high privilege, with no five-level scale.
        # Use positive integers that survive the JSON-to-JavaScript boundary.
        if type(privilege) is not int or not 1 <= privilege <= 2**53 - 1:
            raise ValueError("Action privilegeLevel must be a positive safe integer")

    def _destination_trust(self, function: str, rule: dict[str, Any], arguments: dict[str, Any]) -> str:
        recipients = self._recipients(function, arguments)
        if not recipients or not self._trusted_email_domains:
            return rule.get("destinationTrust", "Trusted")
        domains = {recipient.rsplit("@", 1)[1].lower() for recipient in recipients}
        return "Trusted" if domains.issubset(self._trusted_email_domains) else "Untrusted"

    @classmethod
    def _recipients(cls, function: str, arguments: dict[str, Any]) -> list[str]:
        values: list[Any] = []
        for key in cls.RECIPIENT_FIELDS.get(function, ()):
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
        policy_mode: str = "full-history",
    ) -> None:
        if review_policy not in {"approve", "deny"}:
            raise ValueError("review_policy must be approve or deny")
        if policy_mode not in {"full-history", "point-only"}:
            raise ValueError("policy_mode must be full-history or point-only")
        self.bridge = bridge
        self.catalog = catalog
        self.session_id = session_id
        self.review_policy = review_policy
        self.policy_mode = policy_mode
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
        if "agent_flight_recorder_session_id" in extra_args:
            session_id = extra_args["agent_flight_recorder_session_id"]
        elif self.session_id is not None:
            session_id = self.session_id
        else:
            session_id = str(uuid.uuid4())
        for tool_call in messages[-1]["tool_calls"]:
            try:
                # Assess the exact argument values that the runtime will receive.
                # AgentDojo accepts list-valued arguments serialized as strings.
                arguments = deepcopy(tool_call.args)
                for key, value in arguments.items():
                    if isinstance(value, str) and is_string_list(value):
                        arguments[key] = literal_eval(value)
                action = self.catalog.action(tool_call.function, session_id, arguments)
                TrustedToolCatalog.validate_action(action)
                assessment = self.bridge.request({
                    "command": "assess", "action": action, "policyMode": self.policy_mode
                })["assessment"]
            except Exception as error:
                event = {"tool": tool_call.function, "policyMode": self.policy_mode,
                         "decision": "Block", "executed": False, "error": str(error)}
                audit.append(event)
                self._emit(event)
                results.append(self._error_result(tool_call, str(error)))
                continue

            approved = assessment["decision"] != "Review" or self.review_policy == "approve"
            if assessment["decision"] == "Block" or not approved:
                reason = "; ".join(assessment.get("reasons", [])) or "Policy denied the tool call"
                event = {
                    "tool": tool_call.function,
                    "policyMode": self.policy_mode,
                    "action": action,
                    "assessment": assessment,
                    "approved": approved,
                    "executed": False,
                }
                audit.append(event)
                self._emit(event)
                results.append(self._error_result(tool_call, reason))
                continue

            tool_result, error = runtime.run_function(env, tool_call.function, arguments)
            if error is None:
                self.bridge.request({"command": "record", "action": action})
            event = {
                "tool": tool_call.function,
                "policyMode": self.policy_mode,
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
