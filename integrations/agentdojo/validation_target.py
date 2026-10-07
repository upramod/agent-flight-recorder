"""Run one fresh AgentDojo target trial, without auxiliary benchmark runs."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from agentdojo.agent_pipeline import AgentPipeline, InitQuery, SystemMessage, ToolsExecutionLoop, ToolsExecutor
from agentdojo.agent_pipeline.agent_pipeline import load_system_message
from agentdojo.agent_pipeline.llms import openai_llm
from agentdojo.functions_runtime import EmptyEnv
from agentdojo.logging import OutputLogger, TraceLogger
from agentdojo.task_suite.load_suites import get_suite

from flight_recorder_executor import FlightRecorderToolsExecutor, PolicyBridge, TrustedToolCatalog
from model_preflight import client_for, deployment_for
from safe_environment import load_safe_environment


ROOT = Path(__file__).resolve().parents[2]
MAX_MODEL_CALLS = 48
MAX_COMPLETION_TOKENS = 2048
ARMS = {"baseline", "point-only", "full-history"}


class TargetExecutionError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _safe_error(error: Exception) -> dict[str, Any]:
    """Never serialize provider exception text, headers, bodies, or endpoints."""
    code = getattr(error, "code", None)
    status = getattr(error, "status_code", None)
    return {
        "type": type(error).__name__,
        "code": code if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", code) else None,
        "statusCode": status if type(status) is int else None,
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _usage(usage: Any) -> dict[str, int] | None:
    if usage is None:
        return None
    result = {}
    for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(field) if isinstance(usage, dict) else getattr(usage, field, None)
        if type(value) is int:
            result[field] = value
    return result


class BoundedCompletions:
    """Count requests with SDK and AgentDojo request retries disabled."""

    def __init__(self, client: Any, expected_model: str, path: Path) -> None:
        self.client = client
        self.expected_model = expected_model
        self.path = path
        self.records: list[dict[str, Any]] = []
        self.path.write_text("", encoding="utf-8")

    def create(self, **kwargs: Any) -> Any:
        if len(self.records) >= MAX_MODEL_CALLS:
            raise TargetExecutionError("model_call_budget_exhausted")
        kwargs["temperature"] = 0
        kwargs["max_completion_tokens"] = MAX_COMPLETION_TOKENS
        kwargs.pop("max_tokens", None)
        started = time.perf_counter()
        record = {
            "logicalCall": len(self.records) + 1,
            "requestedModel": kwargs.get("model"),
            "temperature": 0,
            "maxCompletionTokens": MAX_COMPLETION_TOKENS,
            "maxModelCalls": MAX_MODEL_CALLS,
            "transportRetries": 0,
            "status": "requested",
        }
        try:
            response = self.client.chat.completions.create(**kwargs)
            record.update(responseModel=getattr(response, "model", None),
                          usage=_usage(getattr(response, "usage", None)),
                          systemFingerprint=getattr(response, "system_fingerprint", None))
            if record["responseModel"] != self.expected_model:
                raise TargetExecutionError("response_model_identity_drift")
            record["status"] = "completed"
            return response
        except Exception as error:
            record.update(status="error", error=_safe_error(error))
            raise
        finally:
            record["durationSeconds"] = time.perf_counter() - started
            self.records.append(record)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")


class SingleRequestOpenAILLM(openai_llm.OpenAILLM):
    """Pinned OpenAILLM behavior with its extra Tenacity retry layer removed."""

    def query(self, query, runtime, env=EmptyEnv(), messages=(), extra_args=None):
        openai_messages = [openai_llm._message_to_openai(message, self.model) for message in messages]
        openai_tools = [openai_llm._function_to_openai(tool) for tool in runtime.functions.values()]
        # AgentDojo 0.1.35 applies three retries above the SDK and replaces 0 with
        # NOT_GIVEN. Use its undecorated request and enforce 0 in the client proxy.
        completion = openai_llm.chat_completion_request.__wrapped__(
            self.client, self.model, openai_messages, openai_tools, self.reasoning_effort, self.temperature
        )
        output = openai_llm._openai_to_assistant_message(completion.choices[0].message)
        return query, runtime, env, [*messages, output], extra_args or {}


class NormalizedToolsExecutor(ToolsExecutor):
    """Use the pinned list parser without mutating prior assistant arguments."""

    def query(self, query, runtime, env=EmptyEnv(), messages=(), extra_args=None):
        next_query, next_runtime, next_env, next_messages, next_args = super().query(
            query, runtime, env, deepcopy(messages), extra_args or {}
        )
        # The gated executor preserves the model's original proposal in its
        # conversational trace. Give baseline the same subsequent model input.
        results = list(next_messages[len(messages):])
        calls = {call.id: call for call in (messages[-1].get("tool_calls") or [])} if messages else {}
        for result in results:
            if result.get("tool_call_id") in calls:
                result["tool_call"] = calls[result["tool_call_id"]]
        return next_query, next_runtime, next_env, [*messages, *results], next_args


def run_target(config: dict, arm: str, user_task_id: str, injection_task_id: str | None,
               injections: dict, output_dir: Path, manifest_sha: str) -> dict:
    """Persist a terminal result for one isolated target attempt.

    ``output_dir`` must be new, empty, or contain only the parent's matching
    injections.json. Infrastructure and parsing errors have null outcomes,
    never false outcomes. No benchmark feasibility run is made.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    entries = list(output_dir.iterdir())
    if any(path.name != "injections.json" or not path.is_file() for path in entries):
        raise ValueError("Target output directory must be empty except for injections.json")
    if entries and json.loads((output_dir / "injections.json").read_text(encoding="utf-8")) != injections:
        raise ValueError("Target injection file does not match the requested payload")
    start = time.perf_counter()
    session_id = str(uuid.uuid4())
    result = {
        "status": "error", "valid": False, "utility": None, "attack_success": None,
        "error": None, "arm": arm, "user_task_id": user_task_id,
        "injection_task_id": injection_task_id, "manifest_sha": manifest_sha,
        "model_slot": config.get("slot"), "response_model": config.get("responseModel"),
        "session_id": session_id, "created_at": datetime.now(timezone.utc).isoformat(),
        "injections": {}, "tool_messages": [], "policy_denials": [],
        "sdk_transport_retries": 0, "agentdojo_extra_request_retries": 0,
        "max_model_calls": MAX_MODEL_CALLS, "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "cleanup_error": None,
    }
    policy_path = output_dir / "policy.jsonl"
    usage_path = output_dir / "request-usage.jsonl"
    policy_path.write_text("", encoding="utf-8")
    usage_path.write_text("", encoding="utf-8")
    bridge = None
    client = None
    proxy = None
    trace = None
    raw_trace_path = None
    try:
        if arm not in ARMS:
            raise TargetExecutionError("unknown_arm")
        if not isinstance(config.get("responseModel"), str) or not config["responseModel"]:
            raise TargetExecutionError("missing_verified_response_model")
        if not isinstance(injections, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                                 for k, v in injections.items()):
            raise TargetExecutionError("invalid_injections")
        if injection_task_id is None and injections:
            raise TargetExecutionError("clean_task_has_injections")
        result["injections"] = deepcopy(injections)
        suite = get_suite("v1.2.2", "workspace")
        user_task = suite.user_tasks[user_task_id]
        injection_task = suite.injection_tasks[injection_task_id] if injection_task_id is not None else None
        deployment = deployment_for(config)
        if not deployment:
            raise TargetExecutionError("missing_deployment")
        # Freeze only non-secret run settings, never arbitrary provider config.
        # An exclusive create prevents replacing this record after observing a
        # target response. The caller also refuses any existing trial artifacts.
        immutable_config = {
            "provider": config.get("provider"), "deployment": deployment,
            "responseModel": config["responseModel"], "suite": "workspace",
            "benchmarkVersion": "v1.2.2", "agentdojoPackageVersion": "0.1.35",
            "arm": arm, "reviewPolicy": "deny", "trustedEmailDomain": "bluesparrowtech.com",
            "temperature": 0, "maxCompletionTokens": MAX_COMPLETION_TOKENS,
            "maxModelCalls": MAX_MODEL_CALLS, "toolLoopMaxIterations": 15,
            "suiteMaxPipelinePasses": 3, "sdkTransportRetries": 0,
            "agentdojoExtraRequestRetries": 0, "requestTimeoutSeconds": 60,
            "environmentLoader": "parsed-scalars-v1" if os.getenv("STUDY_SAFE_ENVIRONMENT") == "1" else "agentdojo-0.1.35-yaml-interpolation",
            "rateLimitRecovery": {"enabled": os.getenv("STUDY_RATE_LIMIT_RECOVERY") == "1",
                                  "maximumPhysicalAttempts": 6, "retryOnlyStatus": 429,
                                  "retryWaitSeconds": 60, "requestPacingSeconds": 1},
            "catalogSha256": hashlib.sha256(Path(__file__).with_name("workspace-policy.json").read_bytes()).hexdigest(),
        }
        canonical_config = json.dumps(immutable_config, sort_keys=True, separators=(",", ":"), allow_nan=False)
        canonical_injections = json.dumps(injections, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        before_call = {
            "recordedAt": datetime.now(timezone.utc).isoformat(), "manifestSha256": manifest_sha,
            "modelSlot": config.get("slot"), "userTask": user_task_id,
            "injectionTask": injection_task_id, "arm": arm, "sessionId": session_id,
            "injectionsSha256": hashlib.sha256(canonical_injections.encode("utf-8")).hexdigest(),
            "injectionsSha256Encoding": "UTF-8 JSON with sorted keys, compact separators, ensure_ascii=False",
            "configuration": immutable_config,
            "configurationSha256": hashlib.sha256(canonical_config.encode("utf-8")).hexdigest(),
        }
        with (output_dir / "before-call.json").open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(before_call, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        client = client_for(config)
        proxy = BoundedCompletions(client, config["responseModel"], usage_path)
        wrapped_client = SimpleNamespace(chat=SimpleNamespace(completions=proxy))
        llm = SingleRequestOpenAILLM(wrapped_client, deployment, temperature=0)
        if arm == "baseline":
            executor = NormalizedToolsExecutor()
        else:
            bridge = PolicyBridge(ROOT)
            executor = FlightRecorderToolsExecutor(
                bridge, TrustedToolCatalog(Path(__file__).with_name("workspace-policy.json"),
                                           ["bluesparrowtech.com"]),
                session_id=session_id, review_policy="deny", audit_path=policy_path, policy_mode=arm,
            )
        pipeline = AgentPipeline([SystemMessage(load_system_message(None)), InitQuery(), llm,
                                  ToolsExecutionLoop([executor, llm], max_iters=15)])
        pipeline.name = f"afr-v3-{arm}"
        attack_type = "validation-injection" if injection_task is not None else "none"
        raw_trace_path = output_dir / pipeline.name / "workspace" / user_task_id / attack_type / f"{injection_task_id or 'none'}.json"
        with OutputLogger(str(output_dir)) as logger:
            with TraceLogger(logger, suite_name="workspace", pipeline_name=pipeline.name,
                             user_task_id=user_task_id, injection_task_id=injection_task_id,
                             injections=injections, attack_type=attack_type,
                             benchmark_version="v1.2.2", manifest_sha=manifest_sha,
                             arm=arm, response_model=config["responseModel"], session_id=session_id) as trace:
                environment_args = {}
                if os.getenv("STUDY_SAFE_ENVIRONMENT") == "1":
                    environment_args["environment"] = load_safe_environment(suite, injections)
                utility, attack_success = suite.run_task_with_pipeline(
                    pipeline, user_task, injection_task, injections, **environment_args
                )
                if type(utility) is not bool or (injection_task is not None and type(attack_success) is not bool):
                    raise TargetExecutionError("invalid_outcome_type")
                result.update(status="completed", valid=True, utility=utility,
                              attack_success=attack_success if injection_task is not None else None)
                trace.set_contextarg("utility", result["utility"])
                trace.set_contextarg("attack_success", result["attack_success"])
    except Exception as error:
        result.update(status="error", valid=False, utility=None, attack_success=None, error=_safe_error(error))
        if trace is not None:
            trace.log_error(json.dumps(result["error"]))
    finally:
        for resource_name, resource in (("policy_bridge", bridge), ("model_client", client)):
            if resource is not None:
                try:
                    resource.close()
                except Exception as error:
                    if result["cleanup_error"] is None:
                        result["cleanup_error"] = []
                    result["cleanup_error"].append({"resource": resource_name, **_safe_error(error)})

    # Read the saved trace, rather than relying on live mutable message objects.
    try:
        if raw_trace_path is not None and raw_trace_path.exists():
            transcript = json.loads(raw_trace_path.read_text(encoding="utf-8"))
        else:
            transcript = {"messages": [], "error": result["error"], "user_task_id": user_task_id,
                          "injection_task_id": injection_task_id, "arm": arm, "manifest_sha": manifest_sha}
        transcript["error"] = result["error"]
        _write_json(output_dir / "transcript.json", transcript)
        result["tool_messages"] = [message for message in transcript["messages"] if message.get("role") == "tool"]
        policy_events = [json.loads(line) for line in policy_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        result["policy_denials"] = [event for event in policy_events
                                    if event.get("assessment", {}).get("decision", event.get("decision")) in {"Review", "Block"}
                                    and not event.get("executed", False)]
        result["policy_event_count"] = len(policy_events)
    except Exception as error:
        result.update(status="error", valid=False, utility=None, attack_success=None, error=_safe_error(error))
    result["model_calls"] = len(proxy.records) if proxy is not None else 0
    result["duration_seconds"] = time.perf_counter() - start
    _write_json(output_dir / "result.json", result)
    return result
