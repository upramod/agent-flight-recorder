import { ActionEvent, Assessment, Decision } from "./types.js";
import { artifactsFromHistory, resolveLineage } from "./lineage.js";

const clamp = (value: number, min: number, max: number) =>
  Math.max(min, Math.min(max, value));

export class FlightRecorder {
  private readonly sessions = new Map<string, ActionEvent[]>();

  assess(action: ActionEvent, record = true): Assessment {
    const history = this.sessions.get(action.sessionId) ?? [];
    if (action.dataFlow) {
      try {
        const lineage = resolveLineage(action, artifactsFromHistory(history));
        const reasons: string[] = [];
        let score = 0;
        const sensitive = lineage.sensitivity === "Restricted" || lineage.sensitivity === "Confidential";
        if (lineage.untrusted) { score += 20; reasons.push("this artifact depends on untrusted input"); }
        if (lineage.sensitivity === "Restricted") { score += 25; reasons.push("artifact lineage carries Restricted data"); }
        else if (lineage.sensitivity === "Confidential") { score += 15; reasons.push("artifact lineage carries Confidential data"); }
        if (action.privilegeLevel >= 4) { score += 15; reasons.push("high privilege action"); }
        if (action.destinationTrust === "Untrusted") { score += 30; reasons.push("destination is untrusted"); }
        else if (action.destinationTrust === "Unknown") { score += 15; reasons.push("destination trust is unknown"); }
        if (action.operation === "upload" && sensitive && action.destinationTrust !== "Trusted") {
          score = Math.max(score, 70);
          reasons.push("sensitive artifact cannot leave the trusted boundary");
        }
        score = clamp(score, 0, 100);
        return { actionId: action.id, score, reasons, decision: score >= 70 ? "Block" : score >= 40 ? "Review" : "Allow",
          historyLength: history.length, effectiveSensitivity: lineage.sensitivity, sourceArtifactIds: lineage.sources };
      } catch (error) {
        return { actionId: action.id, score: 100, decision: "Block", historyLength: history.length,
          reasons: [error instanceof Error ? error.message : "Artifact lineage could not be resolved"] };
      }
    }
    const reasons: string[] = [];
    let score = 0;

    if (action.inputProvenance === "UntrustedDocument" || action.inputProvenance === "External") {
      score += 20;
      reasons.push(action.inputProvenance === "External"
        ? "input came from an external system"
        : "input came from an untrusted document");
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
      event => event.inputProvenance === "UntrustedDocument" || event.inputProvenance === "External"
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

    // A state-changing action directed outside the trusted boundary after external
    // input is a prompt-injection boundary crossing even when the payload itself
    // is not classified as sensitive. Keep this at Review rather than Block so an
    // interactive deployment can require explicit authorization.
    if (hasUntrustedInput && action.destinationTrust === "Untrusted") {
      score = Math.max(score, 40);
      reasons.push("untrusted input is followed by a state-changing action to an untrusted destination");
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
    if (action.dataFlow) resolveLineage(action, artifactsFromHistory(history));
    history.push(structuredClone(action));
    this.sessions.set(action.sessionId, history);
  }

  history(sessionId: string): ActionEvent[] {
    return structuredClone(this.sessions.get(sessionId) ?? []);
  }
}
