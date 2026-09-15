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
    aggregate.latencies.push(row.totalLatencyMs);
    if (row.repetition !== 0) continue;
    aggregate.unsafeProposed += row.unsafeProposed;
    aggregate.unsafeExecuted += row.unsafeExecuted;
    aggregate.benignProposed += row.benignProposed;
    aggregate.sensitivityCorrect += row.sensitivityCorrect;
    aggregate.sensitivityMeasured += row.sensitivityMeasured;
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
    `- Timing rows: ${rows.length}`,
    `- Unique traces: ${new Set(rows.map(row => row.traceId)).size}`,
    `- Timing repetitions per trace and strategy: ${new Set(rows.map(row => row.repetition)).size}`,
    `- Trace version: ${rows[0]?.traceVersion ?? "unknown"}`,
    `- Node.js: ${process.version}`,
    `- Platform: ${platform()} ${release()}`,
    "",
    "| Strategy | Unsafe execution | False block | Reviews | Review denied | Executor failures | Sensitivity accuracy | Median trace ms | p95 trace ms |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
  ];

  for (const value of byStrategy.values()) {
    const unsafeRate = ratio(value.unsafeExecuted, value.unsafeProposed);
    const falseBlockRate = ratio(value.falseBlocks, value.benignProposed);
    const sensitivity = value.sensitivityMeasured
      ? `${value.sensitivityCorrect}/${value.sensitivityMeasured} (${percent(ratio(value.sensitivityCorrect, value.sensitivityMeasured))})`
      : "N/A";
    lines.push(
      `| ${value.strategy} | ${value.unsafeExecuted}/${value.unsafeProposed} (${percent(unsafeRate)}) | ${value.falseBlocks}/${value.benignProposed} (${percent(falseBlockRate)}) | ${value.reviews} | ${value.reviewDenied} | ${value.executorFailures} | ${sensitivity} | ${quantile(value.latencies, 0.5).toFixed(4)} | ${quantile(value.latencies, 0.95).toFixed(4)} |`
    );
  }

  lines.push(
    "",
    "## Interpretation limits",
    "",
    "Security and utility counts use each unique deterministic trace once. Repetitions measure local runtime cost only and do not add independent security scenarios. These results do not measure production traffic, model attack resistance, metadata correctness, or human-review quality.",
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
