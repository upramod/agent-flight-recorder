import { randomUUID } from "node:crypto";
import { proposeAzureAction } from "./azureAgent.js";
import { ExecutionGate } from "./gate.js";
import { FlightRecorder } from "./engine.js";

try {
  const action = await proposeAzureAction(
    "Synthetic task: start by reading the supplied sandbox document. No actions have executed yet.",
    randomUUID()
  );
  if (!action) {
    console.log("Azure proposed stopping. No tool executed.");
  } else {
    const gate = new ExecutionGate(new FlightRecorder());
    // Synchronous mock only: never performs filesystem or network tool effects.
    const result = gate.evaluate(action, () => ({ synthetic: true }), false);
    console.log(JSON.stringify({ mode: "azure-proposal-mock-tools", action, result }, null, 2));
  }
} catch (error) {
  console.error(error instanceof Error ? error.message : "Azure proposal failed");
  process.exitCode = 1;
}
