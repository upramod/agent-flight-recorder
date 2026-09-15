import { readFileSync, writeFileSync } from "node:fs";
import { platform, release } from "node:os";
import { pathToFileURL } from "node:url";
import type { BenchmarkRow, StrategyName } from "./benchmark.js";

interface Aggregate {
  strategy: StrategyName;
  unsafeProposed: number;
  unsafeExecuted: number;
  benignProposed: number;
  falseBlocks: number;
  reviews: number;
  reviewDenied: number;
  executorFailures: number;
  sensitivityCorrect: number;
  sensitivityMeasured: number;
  latencies: number[];
}

function ratio(numerator: number, denominator: number): number {
  return denominator ? numerator / denominator : 0;
}

function percent(value: number): string {
  return (value * 100).toFixed(1) + "%";
}

function wilson(successes: number, total: number): [number, number] {
  if (!total) return [0, 0];
  const z = 1.959963984540054;
  const p = successes / total;
  const denominator = 1 + (z * z) / total;
  const center = (p + (z * z) / (2 * total)) / denominator;
  const margin = z * Math.sqrt((p * (1 - p) + (z * z) / (4 * total)) / total) / denominator;
  return [Math.max(0, center - margin), Math.min(1, center + margin)];
}

function quantile(values: number[], q: number): number {
  const ordered = [...values].sort((a, b) => a - b);
  if (!ordered.length) return 0;
  const index = Math.min(ordered.length - 1, Math.floor(q * ordered.length));
  return ordered[index];
}

export function summarize(rows: BenchmarkRow[]): string {
  const byStrategy = new Map<StrategyName, Aggregate>();
  for (const row of rows) {
    let aggregate = byStrategy.get(row.strategy);
    if (!aggregate) {
      aggregate = {
        strategy: row.strategy,
        unsafeProposed: 0,
        unsafeExecuted: 0,
        benignProposed: 0,
        falseBlocks: 0,
        reviews: 0,
        reviewDenied: 0,
        executorFailures: 0,
        sensitivityCorrect: 0,
        sensitivityMeasured: 0,
        latencies: []
      };
      byStrategy.set(row.strategy, aggregate);
    }
    aggregate.unsafeProposed += row.unsafeProposed;
    aggregate.unsafeExecuted += row.unsafeExecuted;
    aggregate.benignProposed += row.benignProposed;
    aggregate.sensitivityCorrect += row.sensitivityCorrect;
    aggregate.sensitivityMeasured += row.sensitivityMeasured;
    aggregate.latencies.push(row.totalLatencyMs);
    for (const action of row.actions) {
      if (!action.unsafe && action.decision === "Block") aggregate.falseBlocks++;
      if (action.decision === "Review") aggregate.reviews++;
      if (action.decision === "Review" && !action.executed) aggregate.reviewDenied++;
      if (action.decision === "ExecutorFailure") aggregate.executorFailures++;
    }
  }

  const lines = [
    "# Deterministic benchmark summary",
    "",
    "Generated from JSONL benchmark output. Latency covers one complete synthetic trace and excludes model, network, and human-review time.",
    "",
    `- Rows: ${rows.length}`,
    `- Trace version: ${rows[0]?.traceVersion ?? "unknown"}`,
    `- Node.js: ${process.version}`,
    `- Platform: ${platform()} ${release()}`,
    "",
    "| Strategy | Unsafe execution | 95% CI | False block | Reviews | Review denied | Executor failures | Sensitivity accuracy | Median trace ms | p95 trace ms |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
  ];

  for (const value of byStrategy.values()) {
    const unsafeRate = ratio(value.unsafeExecuted, value.unsafeProposed);
    const [low, high] = wilson(value.unsafeExecuted, value.unsafeProposed);
    const falseBlockRate = ratio(value.falseBlocks, value.benignProposed);
    const sensitivity = value.sensitivityMeasured
      ? `${value.sensitivityCorrect}/${value.sensitivityMeasured} (${percent(ratio(value.sensitivityCorrect, value.sensitivityMeasured))})`
      : "N/A";
    lines.push(
      `| ${value.strategy} | ${value.unsafeExecuted}/${value.unsafeProposed} (${percent(unsafeRate)}) | ${percent(low)}–${percent(high)} | ${value.falseBlocks}/${value.benignProposed} (${percent(falseBlockRate)}) | ${value.reviews} | ${value.reviewDenied} | ${value.executorFailures} | ${sensitivity} | ${quantile(value.latencies, 0.5).toFixed(4)} | ${quantile(value.latencies, 0.95).toFixed(4)} |`
    );
  }

  lines.push(
    "",
    "## Interpretation limits",
    "",
    "Repeated deterministic traces measure implementation behavior and local runtime cost. Repetitions do not add independent security scenarios. Report both the number of unique traces and the number of timing repetitions. These results do not measure production traffic, model attack resistance, metadata correctness, or human-review quality.",
    ""
  );
  return lines.join("\n");
}

function main() {
  const input = process.argv[2] ?? "results/benchmark.jsonl";
  const output = process.argv[3] ?? "results/benchmark-summary.md";
  const rows = readFileSync(input, "utf8")
    .split(/\r?\n/)
    .filter(Boolean)
    .map(line => JSON.parse(line) as BenchmarkRow);
  if (!rows.length) throw new Error("benchmark input is empty");
  writeFileSync(output, summarize(rows), "utf8");
  process.stderr.write(`wrote summary to ${output}\n`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main();
