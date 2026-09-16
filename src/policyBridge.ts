import { createInterface } from "node:readline";
import { FlightRecorder } from "./engine.js";
import type { ActionEvent } from "./types.js";

type Request =
  | { command: "assess"; action: ActionEvent }
  | { command: "record"; action: ActionEvent }
  | { command: "history"; sessionId: string };

export function handleBridgeRequest(recorder: FlightRecorder, request: Request): Record<string, unknown> {
  if (!request || typeof request !== "object") throw new Error("Invalid bridge request");
  if (request.command === "assess") return { assessment: recorder.assess(request.action, false) };
  if (request.command === "record") {
    recorder.record(request.action);
    return { recorded: true };
  }
  if (request.command === "history") return { history: recorder.history(request.sessionId) };
  throw new Error("Unknown bridge command");
}

function main(): void {
  const recorder = new FlightRecorder();
  const input = createInterface({ input: process.stdin, crlfDelay: Infinity });
  input.on("line", line => {
    try {
      const request = JSON.parse(line) as Request;
      process.stdout.write(JSON.stringify({ ok: true, ...handleBridgeRequest(recorder, request) }) + "\n");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Bridge request failed";
      process.stdout.write(JSON.stringify({ ok: false, error: message }) + "\n");
    }
  });
}

if (process.argv[1]?.endsWith("policyBridge.js")) main();
