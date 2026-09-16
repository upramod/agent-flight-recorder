import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { pathToFileURL } from "node:url";
import { benchmarkTraces, runTrace } from "./benchmark.js";
import type { BenchmarkTrace } from "./benchmark.js";

const targetTraceIds = [
  "restricted-external-export",
  "mixed-source-export",
  "multi-generation-restricted-export"
] as const;

export interface LabelErrorRow {
  study: "sensitivity_downgrade";
  traceId: string;
  probability: number;
  trials: number;
  seed: number;
  corruptedTrials: number;
  unsafeExecuted: number;
  unsafeExecutionRate: number;
}

export interface StructuralErrorRow {
  study: "structural_error";
  traceId: string;
  error: "producer_lineage_omitted" | "wrong_input_reference" | "all_lineage_omitted" | "lineage_and_label_omitted";
  unsafeExecuted: number;
  unsafeProposed: number;
  terminalDecisions: string[];
}

export interface MetadataErrorStudy {
  schemaVersion: 1;
  trialsPerProbability: number;
  seed: number;
  probabilities: number[];
  labelErrors: LabelErrorRow[];
  structuralErrors: StructuralErrorRow[];
}

function cloneTrace(id: string): BenchmarkTrace {
  const trace = benchmarkTraces.find(item => item.id === id);
  if (!trace) throw new Error("Missing benchmark trace: " + id);
  return structuredClone(trace);
}

function generator(seed: number) {
  let state = seed >>> 0;
  return () => {
    state = (1664525 * state + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

function downgradeSensitiveLabels(trace: BenchmarkTrace): number {
  let changed = 0;
  for (const action of trace.actions) {
    if (action.sensitivity === "Restricted" || action.sensitivity === "Confidential") {
      action.sensitivity = "Public";
      changed++;
    }
  }
  return changed;
}

function finalUnsafeExecuted(trace: BenchmarkTrace): { executed: number; decisions: string[] } {
  const row = runTrace(trace, "artifact_aware");
  const unsafe = new Set(trace.unsafeActionIds);
  return {
    executed: row.actions.filter(action => action.unsafe && action.executed).length,
    decisions: row.actions.filter(action => unsafe.has(action.actionId)).map(action => action.decision)
  };
}

function structuralCases(): StructuralErrorRow[] {
  const rows: StructuralErrorRow[] = [];

  {
    const trace = cloneTrace("restricted-external-export");
    delete trace.actions[0].dataFlow;
    const result = finalUnsafeExecuted(trace);
    rows.push({ study: "structural_error", traceId: trace.id, error: "producer_lineage_omitted",
      unsafeExecuted: result.executed, unsafeProposed: trace.unsafeActionIds.length, terminalDecisions: result.decisions });
  }

  {
    const trace = cloneTrace("restricted-external-export");
    const upload = trace.actions.find(action => action.id === "res-upload");
    if (!upload?.dataFlow) throw new Error("Expected upload lineage");
    upload.dataFlow.inputs = ["unknown-export"];
    const result = finalUnsafeExecuted(trace);
    rows.push({ study: "structural_error", traceId: trace.id, error: "wrong_input_reference",
      unsafeExecuted: result.executed, unsafeProposed: trace.unsafeActionIds.length, terminalDecisions: result.decisions });
  }

  {
    const trace = cloneTrace("restricted-external-export");
    trace.actions.forEach(action => delete action.dataFlow);
    const result = finalUnsafeExecuted(trace);
    rows.push({ study: "structural_error", traceId: trace.id, error: "all_lineage_omitted",
      unsafeExecuted: result.executed, unsafeProposed: trace.unsafeActionIds.length, terminalDecisions: result.decisions });
  }

  {
    const trace = cloneTrace("restricted-external-export");
    trace.actions.forEach(action => delete action.dataFlow);
    downgradeSensitiveLabels(trace);
    const result = finalUnsafeExecuted(trace);
    rows.push({ study: "structural_error", traceId: trace.id, error: "lineage_and_label_omitted",
      unsafeExecuted: result.executed, unsafeProposed: trace.unsafeActionIds.length, terminalDecisions: result.decisions });
  }

  return rows;
}

export function runMetadataErrorStudy(
  trialsPerProbability = 1000,
  seed = 20260916,
  probabilities = [0, 0.1, 0.25, 0.5, 0.75, 1]
): MetadataErrorStudy {
  if (!Number.isInteger(trialsPerProbability) || trialsPerProbability < 1) {
    throw new Error("trialsPerProbability must be a positive integer");
  }
  if (!Number.isInteger(seed) || seed < 0) throw new Error("seed must be a non-negative integer");
  if (!probabilities.length || probabilities.some(value => value < 0 || value > 1)) {
    throw new Error("probabilities must be between 0 and 1");
  }

  const random = generator(seed);
  const labelErrors: LabelErrorRow[] = [];
  for (const traceId of targetTraceIds) {
    for (const probability of probabilities) {
      let corruptedTrials = 0;
      let unsafeExecuted = 0;
      for (let trial = 0; trial < trialsPerProbability; trial++) {
        const trace = cloneTrace(traceId);
        if (random() < probability) {
          corruptedTrials++;
          downgradeSensitiveLabels(trace);
        }
        unsafeExecuted += finalUnsafeExecuted(trace).executed;
      }
      labelErrors.push({
        study: "sensitivity_downgrade",
        traceId,
        probability,
        trials: trialsPerProbability,
        seed,
        corruptedTrials,
        unsafeExecuted,
        unsafeExecutionRate: unsafeExecuted / (trialsPerProbability * cloneTrace(traceId).unsafeActionIds.length)
      });
    }
  }

  return {
    schemaVersion: 1,
    trialsPerProbability,
    seed,
    probabilities,
    labelErrors,
    structuralErrors: structuralCases()
  };
}

function parseArguments(argv: string[]) {
  let trials = 1000;
  let seed = 20260916;
  let output = "results/metadata-error-study.json";
  for (let index = 0; index < argv.length; index++) {
    const name = argv[index];
    const value = argv[++index];
    if (!value) throw new Error("Missing value for " + name);
    if (name === "--trials") trials = Number(value);
    else if (name === "--seed") seed = Number(value);
    else if (name === "--output") output = value;
    else throw new Error("Unknown argument: " + name);
  }
  return { trials, seed, output };
}

function main() {
  const args = parseArguments(process.argv.slice(2));
  const result = runMetadataErrorStudy(args.trials, args.seed);
  mkdirSync(dirname(args.output), { recursive: true });
  writeFileSync(args.output, JSON.stringify(result, null, 2) + "\n", "utf8");
  process.stderr.write(`wrote metadata-error study to ${args.output}\n`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main();
