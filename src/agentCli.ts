import { createInterface } from "node:readline/promises";
import { stdin, stdout } from "node:process";
import { runAgentLoop } from "./agentLoop.js";

const scenario = process.argv[2] ?? "safe";
if (scenario !== "safe" && scenario !== "injection") {
  console.error("Usage: npm run agent -- safe|injection");
  process.exitCode = 1;
} else {
  const terminal = stdin.isTTY ? createInterface({ input: stdin, output: stdout }) : undefined;
  try {
    console.log("Live Azure proposals; synthetic tools. Maximum 8 model requests.");
    console.log("Scenario: " + scenario + ". A model stop is valid and is not a policy block.");
    const result = await runAgentLoop({
      scenario,
      approve: async (action, assessment) => {
        console.log("Review: " + action.tool + "." + action.operation + " score=" + assessment.score);
        console.log(assessment.reasons.join("; "));
        if (!terminal) return false;
        return (await terminal.question("Approve this synthetic action? Type yes to execute: ")).trim().toLowerCase() === "yes";
      },
      onEvent: event => console.log("[" + event.assessment.decision + "] " + event.action.operation +
        " score=" + event.assessment.score + " executed=" + event.executed + " approved=" + event.approved)
    });
    console.log(JSON.stringify(result, null, 2));
    if (["proposal_error", "invalid_session", "execution_or_approval_error"].includes(result.status)) process.exitCode = 1;
  } finally { terminal?.close(); }
}
