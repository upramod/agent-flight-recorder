import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { pathToFileURL } from "node:url";
import { performance } from "node:perf_hooks";
import { runAgentLoop } from "./agentLoop.js";
import type { AgentScenario, LoopOptions } from "./agentLoop.js";

export const MODEL_STUDY_SCHEMA_VERSION = 1;
export const MODEL_STUDY_PROMPT_VERSION = "agent-loop-2026-09-15";
export const modelStudyScenarios: AgentScenario[] = ["safe", "injection", "ambiguous"];

type LoopResult = Awaited<ReturnType<typeof runAgentLoop>>;
type LoopRunner = (options: LoopOptions) => Promise<LoopResult>;

export interface ModelStudyRow {
  schemaVersion: 1;
  promptVersion: string;
  scenario: AgentScenario;
  runIndex: number;
  timestamp: string;
  deployment?: string;
  status: string;
  sessionId: string;
  proposalCount: number;
  executedCount: number;
  durationMs: number;
  approvalPolicy: "approve_all_reviews_scripted";
  proposedOperations: string[];
  decisions: string[];
  executed: boolean[];
  blockedOperation?: string;
  events: LoopResult["events"];
}

export interface ModelStudyOptions {
  runsPerScenario: number;
  scenarios?: AgentScenario[];
  maxSteps?: number;
  delayMs?: number;
  deployment?: string;
  runLoop?: LoopRunner;
  onRow?: (row: ModelStudyRow) => void;
}

function delay(milliseconds: number): Promise<void> {
  return milliseconds > 0
    ? new Promise(resolve => setTimeout(resolve, milliseconds))
    : Promise.resolve();
}

export async function runModelStudy(options: ModelStudyOptions): Promise<ModelStudyRow[]> {
  const scenarios = options.scenarios ?? modelStudyScenarios;
  const maxSteps = options.maxSteps ?? 8;
  const delayMs = options.delayMs ?? 250;
  const runLoop = options.runLoop ?? runAgentLoop;
  if (!Number.isInteger(options.runsPerScenario) || options.runsPerScenario < 1) {
    throw new Error("runsPerScenario must be a positive integer");
  }
  if (!Number.isInteger(maxSteps) || maxSteps < 1 || maxSteps > 8) {
    throw new Error("maxSteps must be 1..8");
  }
  if (!Number.isInteger(delayMs) || delayMs < 0 || delayMs > 60000) {
    throw new Error("delayMs must be 0..60000");
  }
  if (!scenarios.length || scenarios.some(value => !modelStudyScenarios.includes(value))) {
    throw new Error("Unknown model-study scenario");
  }

  const rows: ModelStudyRow[] = [];
  for (const scenario of scenarios) {
    for (let runIndex = 0; runIndex < options.runsPerScenario; runIndex++) {
      const started = performance.now();
      const result = await runLoop({
        scenario,
        maxSteps,
        // This is an experimental policy, not a human approval claim.
        approve: async () => true
      });
      const blocked = result.events.find(event =>
        event.assessment.decision === "Block" && !event.executed
      );
      const row: ModelStudyRow = {
        schemaVersion: MODEL_STUDY_SCHEMA_VERSION,
        promptVersion: MODEL_STUDY_PROMPT_VERSION,
        scenario,
        runIndex,
        timestamp: new Date().toISOString(),
        deployment: options.deployment,
        status: result.status,
        sessionId: result.sessionId,
        proposalCount: result.proposalCount,
        executedCount: result.executedCount,
        durationMs: performance.now() - started,
        approvalPolicy: "approve_all_reviews_scripted",
        proposedOperations: result.events.map(event => event.action.operation),
        decisions: result.events.map(event => event.assessment.decision),
        executed: result.events.map(event => event.executed),
        blockedOperation: blocked?.action.operation,
        events: result.events
      };
      rows.push(row);
      options.onRow?.(structuredClone(row));
      if (runIndex + 1 < options.runsPerScenario) await delay(delayMs);
    }
  }
  return rows;
}

function parseArguments(argv: string[]) {
  let runsPerScenario = 1;
  let output = "results/model-study.jsonl";
  let scenarios = modelStudyScenarios;
  let maxSteps = 8;
  let delayMs = 250;
  for (let index = 0; index < argv.length; index++) {
    const name = argv[index];
    const value = argv[++index];
    if (!value) throw new Error("Missing value for " + name);
    if (name === "--runs") runsPerScenario = Number(value);
    else if (name === "--output") output = value;
    else if (name === "--scenarios") scenarios = value.split(",") as AgentScenario[];
    else if (name === "--max-steps") maxSteps = Number(value);
    else if (name === "--delay-ms") delayMs = Number(value);
    else throw new Error("Unknown argument: " + name);
  }
  return { runsPerScenario, output, scenarios, maxSteps, delayMs };
}

async function main() {
  const endpoint = process.env.AZURE_OPENAI_ENDPOINT;
  const key = process.env.AZURE_OPENAI_API_KEY;
  const deployment = process.env.AZURE_OPENAI_DEPLOYMENT;
  if (!endpoint || !key || !deployment) {
    throw new Error("Azure OpenAI configuration is missing");
  }
  const args = parseArguments(process.argv.slice(2));
  const rows = await runModelStudy({
    ...args,
    deployment,
    onRow: row => process.stderr.write(
      `[${row.scenario} ${row.runIndex + 1}/${args.runsPerScenario}] ${row.status}; proposals=${row.proposalCount}; executed=${row.executedCount}\n`
    )
  });
  mkdirSync(dirname(args.output), { recursive: true });
  writeFileSync(args.output, rows.map(row => JSON.stringify(row)).join("\n") + "\n", "utf8");
  process.stderr.write(`wrote ${rows.length} model-study rows to ${args.output}\n`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => {
    process.stderr.write((error instanceof Error ? error.message : String(error)) + "\n");
    process.exitCode = 1;
  });
}
