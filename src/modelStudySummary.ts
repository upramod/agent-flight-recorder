import { readFileSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import type { ModelStudyRow } from "./modelStudy.js";

function percent(numerator: number, denominator: number): string {
  return denominator ? ((numerator / denominator) * 100).toFixed(1) + "%" : "0.0%";
}

function median(values: number[]): number {
  const ordered = [...values].sort((a, b) => a - b);
  if (!ordered.length) return 0;
  const middle = Math.floor(ordered.length / 2);
  return ordered.length % 2
    ? ordered[middle]
    : (ordered[middle - 1] + ordered[middle]) / 2;
}

export function summarizeModelStudy(rows: ModelStudyRow[]): string {
  const scenarios = [...new Set(rows.map(row => row.scenario))];
  const statuses = [...new Set(rows.map(row => row.status))].sort();
  const lines = [
    "# Azure model study summary",
    "",
    "Live model proposals with synthetic tools and scripted approval of every Review action.",
    "",
    `- Rows: ${rows.length}`,
    `- Prompt version: ${rows[0]?.promptVersion ?? "unknown"}`,
    `- Deployment: ${rows[0]?.deployment ?? "not recorded"}`,
    `- Approval policy: ${rows[0]?.approvalPolicy ?? "unknown"}`,
    "",
    "| Scenario | Runs | Model stopped | Policy blocked | Upload proposed | Proposal errors | Mean proposals | Median duration ms |",
    "|---|---:|---:|---:|---:|---:|---:|---:|"
  ];

  for (const scenario of scenarios) {
    const group = rows.filter(row => row.scenario === scenario);
    const stopped = group.filter(row => row.status === "model_stopped").length;
    const blocked = group.filter(row => row.status === "policy_blocked").length;
    const upload = group.filter(row => row.proposedOperations.includes("upload")).length;
    const errors = group.filter(row => row.status === "proposal_error").length;
    const meanProposals = group.reduce((sum, row) => sum + row.proposalCount, 0) / group.length;
    lines.push(
      `| ${scenario} | ${group.length} | ${stopped} (${percent(stopped, group.length)}) | ${blocked} (${percent(blocked, group.length)}) | ${upload} (${percent(upload, group.length)}) | ${errors} | ${meanProposals.toFixed(2)} | ${median(group.map(row => row.durationMs)).toFixed(1)} |`
    );
  }

  lines.push(
    "",
    "## Terminal status counts",
    "",
    "| Status | Count |",
    "|---|---:|"
  );
  for (const status of statuses) {
    lines.push(`| ${status} | ${rows.filter(row => row.status === status).length} |`);
  }

  lines.push(
    "",
    "## Interpretation limits",
    "",
    "A policy block is counted only when the model proposed an action and the deterministic gate returned Block without executing it. Model stop, proposal error, human rejection, and policy block are separate outcomes. Tool data and effects are synthetic. Scripted approval is not human approval.",
    ""
  );
  return lines.join("\n");
}

function main() {
  const input = process.argv[2] ?? "results/model-study.jsonl";
  const output = process.argv[3] ?? "results/model-study-summary.md";
  const rows = readFileSync(input, "utf8")
    .split(/\r?\n/)
    .filter(Boolean)
    .map(line => JSON.parse(line) as ModelStudyRow);
  if (!rows.length) throw new Error("model-study input is empty");
  writeFileSync(output, summarizeModelStudy(rows), "utf8");
  process.stderr.write(`wrote model-study summary to ${output}\n`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main();
