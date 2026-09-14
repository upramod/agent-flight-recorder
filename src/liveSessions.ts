import { randomUUID } from "node:crypto";
import { runAgentLoop, type LoopOptions, type LoopEvent } from "./agentLoop.js";
import type { ActionEvent, Assessment } from "./types.js";

export class LiveSessions {
  private runs = new Map<string, {
    id: string; scenario: "safe" | "injection"; status: string; events: LoopEvent[]; sessionId?: string;
    pending?: { action: ActionEvent; assessment: Assessment; expiresAt: number };
    resolve?: (approved: boolean) => void;
  }>();
  constructor(private runner: typeof runAgentLoop = runAgentLoop, private approvalMs = 120000) {}
  start(scenario: "safe" | "injection") {
    if ([...this.runs.values()].some(run => ["running", "awaiting_approval"].includes(run.status))) {
      throw new Error("A live run is already active");
    }
    if (this.runs.size >= 20) this.runs.delete(this.runs.keys().next().value!);
    const run: { id: string; scenario: "safe" | "injection"; status: string; events: LoopEvent[]; sessionId?: string;
      pending?: { action: ActionEvent; assessment: Assessment; expiresAt: number };
      resolve?: (approved: boolean) => void } = { id: randomUUID(), scenario, status: "running", events: [] };
    this.runs.set(run.id, run);
    const options: LoopOptions = {
      scenario,
      onEvent: event => { run.events.push(event); run.sessionId = event.action.sessionId; },
      approve: (action, assessment) => new Promise<boolean>(resolve => {
        run.status = "awaiting_approval";
        run.sessionId = action.sessionId;
        run.pending = { action, assessment, expiresAt: Date.now() + this.approvalMs };
        const timer = setTimeout(() => run.resolve?.(false), this.approvalMs);
        run.resolve = approved => {
          clearTimeout(timer);
          delete run.pending;
          delete run.resolve;
          run.status = "running";
          resolve(approved);
        };
      })
    };
    void this.runner(options).then(result => {
      run.status = result.status;
      run.sessionId = result.sessionId;
    }).catch(() => { run.resolve?.(false); run.status = "run_error"; });
    return run.id;
  }
  get(id: string) {
    const run = this.runs.get(id);
    if (!run) return undefined;
    return structuredClone({ id: run.id, scenario: run.scenario, status: run.status, sessionId: run.sessionId,
      events: run.events, pending: run.pending });
  }
  decide(id: string, actionId: string, approved: boolean) {
    const run = this.runs.get(id);
    if (!run?.pending || run.pending.action.id !== actionId || !run.resolve) return false;
    if (Date.now() >= run.pending.expiresAt) { run.resolve(false); return false; }
    run.resolve(approved);
    return true;
  }
}
