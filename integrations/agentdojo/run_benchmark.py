from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Callable, TypeVar

from agentdojo.agent_pipeline import AgentPipeline, InitQuery, SystemMessage, ToolsExecutionLoop, ToolsExecutor
from agentdojo.agent_pipeline.agent_pipeline import load_system_message
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.attacks.attack_registry import load_attack
from agentdojo.benchmark import benchmark_suite_with_injections, benchmark_suite_without_injections
from agentdojo.logging import OutputLogger
from agentdojo.task_suite.load_suites import get_suite
from openai import AzureOpenAI

from flight_recorder_executor import FlightRecorderToolsExecutor, PolicyBridge, TrustedToolCatalog


# AgentDojo 0.1.35 recognizes only a fixed list of model-name tokens when it
# builds model-addressed attack text. GPT-4.1 is absent, so use its GPT-4 alias
# for attack wording while retaining the actual Azure deployment in the name.
AGENTDOJO_ATTACK_MODEL_ALIAS = "gpt-4o-mini-2024-07-18"
T = TypeVar("T")


def pipeline_name(mode: str, review_policy: str, deployment: str) -> str:
    return f"{AGENTDOJO_ATTACK_MODEL_ALIAS}__azure-{deployment}__{mode}-{review_policy}"


def with_output_logger(logdir: Path, operation: Callable[[], T]) -> T:
    with OutputLogger(str(logdir)):
        return operation()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AgentDojo through Agent Flight Recorder")
    parser.add_argument("--suite", default="workspace")
    parser.add_argument("--benchmark-version", default="v1.2.2")
    parser.add_argument("--user-task", action="append")
    parser.add_argument("--injection-task", action="append")
    parser.add_argument("--attack", default="tool_knowledge")
    parser.add_argument("--review-policy", choices=("approve", "deny"), default="approve")
    parser.add_argument("--mode", choices=("baseline", "flight-recorder"), default="flight-recorder")
    parser.add_argument("--catalog", type=Path, default=Path(__file__).with_name("workspace-policy.json"))
    parser.add_argument("--trusted-email-domain", action="append", default=[])
    parser.add_argument("--logdir", type=Path, default=Path("results/agentdojo"))
    parser.add_argument("--force-rerun", action="store_true")
    return parser.parse_args()


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing {name}")
    return value


def main() -> None:
    args = arguments()
    root = Path(__file__).resolve().parents[2]
    bridge = PolicyBridge(root)
    try:
        client = AzureOpenAI(
            azure_endpoint=required("AZURE_OPENAI_ENDPOINT"),
            api_key=required("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
        )
        deployment = required("AZURE_OPENAI_DEPLOYMENT")
        llm = OpenAILLM(client, deployment)
        executor = (
            ToolsExecutor()
            if args.mode == "baseline"
            else FlightRecorderToolsExecutor(
                bridge,
                TrustedToolCatalog(args.catalog, args.trusted_email_domain),
                review_policy=args.review_policy,
                audit_path=args.logdir / "flight-recorder-policy.jsonl",
            )
        )
        pipeline = AgentPipeline([
            SystemMessage(load_system_message(None)),
            InitQuery(),
            llm,
            ToolsExecutionLoop([executor, llm]),
        ])
        pipeline.name = pipeline_name(args.mode, args.review_policy, deployment)
        suite = get_suite(args.benchmark_version, args.suite)
        args.logdir.mkdir(parents=True, exist_ok=True)
        common = dict(
            user_tasks=args.user_task,
            logdir=args.logdir,
            force_rerun=args.force_rerun,
            benchmark_version=args.benchmark_version,
        )
        def run():
            if args.attack:
                attack = load_attack(args.attack, suite, pipeline)
                return benchmark_suite_with_injections(
                    pipeline,
                    suite,
                    attack,
                    injection_tasks=args.injection_task,
                    **common,
                )
            return benchmark_suite_without_injections(pipeline, suite, **common)

        result = with_output_logger(args.logdir, run)
        utility = list(result["utility_results"].values())
        security = list(result["security_results"].values())
        print(f"utility={sum(utility)}/{len(utility)}")
        if security:
            print(f"security={sum(security)}/{len(security)}")
        print(f"logs={args.logdir}")
        print(f"mode={args.mode}")
    finally:
        bridge.close()


if __name__ == "__main__":
    main()
