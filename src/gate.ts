import { FlightRecorder } from "./engine.js";
import { ActionEvent, Assessment, Decision } from "./types.js";

export type ToolExecutor<T> = (action: ActionEvent) => T;

export interface GateResult<T> {
  assessment: Assessment;
  executed: boolean;
  output?: T;
  approvalRequired: boolean;
}

export class ExecutionGate {
  constructor(private readonly recorder: FlightRecorder) {}

  evaluate<T>(
    action: ActionEvent,
    execute: ToolExecutor<T>,
    approved = false
  ): GateResult<T> {
    action = structuredClone(action);
    const assessment = this.recorder.assess(action, false);

    if (assessment.decision === "Block") {
      return { assessment, executed: false, approvalRequired: false };
    }

    if (assessment.decision === "Review" && !approved) {
      return { assessment, executed: false, approvalRequired: true };
    }

    const output = execute(structuredClone(action));
    this.recorder.record(action);

    return {
      assessment,
      executed: true,
      approvalRequired: false,
      output
    };
  }
}
