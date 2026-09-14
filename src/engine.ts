import { ActionEvent, Assessment, Decision } from "./types.js";

const clamp = (value: number, min: number, max: number) =>
  Math.max(min, Math.min(max, value));

export class FlightRecorder {
  private readonly sessions = new Map<string, ActionEvent[]>();

  assess(action: ActionEvent, record = true): Assessment {
    const history = this.sessions.get(action.sessionId) ?? [];
    const reasons: string[] = [];
    let score = 0;

    if (action.inputProvenance === "UntrustedDocument") {
      score += 20;
      reasons.push("input came from an untrusted document");
    }

    if (action.sensitivity === "Restricted") {
      score += 25;
      reasons.push("action touches restricted data");
    } else if (action.sensitivity === "Confidential") {
      score += 15;
      reasons.push("action touches confidential data");
    }

    if (action.destinationTrust === "Unknown") {
      score += 15;
      reasons.push("destination trust is unknown");
    } else if (action.destinationTrust === "Untrusted") {
      score += 30;
      reasons.push("destination is untrusted");
    }

    if (action.privilegeLevel >= 4) {
      score += 15;
      reasons.push("high privilege action");
    }

    const hasUntrustedInput = history.some(
      event => event.inputProvenance === "UntrustedDocument"
    );
    const accessedSensitiveData = history.some(
      event => event.sensitivity === "Confidential" || event.sensitivity === "Restricted"
    );
    const createdExport = history.some(
      event => event.operation === "create_export" || event.resourceType === "data_export"
    );

    const currentActionTouchesSensitiveData =
      action.sensitivity === "Confidential" || action.sensitivity === "Restricted";

    if (hasUntrustedInput && (accessedSensitiveData || currentActionTouchesSensitiveData)) {
      score += 20;
      reasons.push("untrusted input is followed by sensitive-data access");
    }

    if (accessedSensitiveData && createdExport && action.operation === "upload") {
      score += 30;
      reasons.push("export upload follows sensitive-data access");
    }

    if (createdExport && action.operation === "upload" && action.destinationTrust !== "Trusted") {
      score += 20;
      reasons.push("export is leaving the trusted boundary");
    }

    score = clamp(score, 0, 100);
    const decision: Decision =
      score >= 70 ? "Block" : score >= 40 ? "Review" : "Allow";

    const assessment: Assessment = {
      actionId: action.id,
      score,
      reasons,
      decision,
      historyLength: history.length
    };

    if (record) this.record(action);
    return assessment;
  }

  record(action: ActionEvent): void {
    const history = this.sessions.get(action.sessionId) ?? [];
    history.push(action);
    this.sessions.set(action.sessionId, history);
  }

  history(sessionId: string): ActionEvent[] {
    return [...(this.sessions.get(sessionId) ?? [])];
  }
}
