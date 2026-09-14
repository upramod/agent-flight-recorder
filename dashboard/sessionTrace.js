// Export only runtime trace fields. No configuration or model response envelopes.
function actionFields(action) {
  const { id, sessionId, timestamp, tool, operation, resourceType, sensitivity,
    destinationTrust, privilegeLevel, inputProvenance, dataFlow, metadata } = action;
  return { id, sessionId, timestamp, tool, operation, resourceType, sensitivity,
    destinationTrust, privilegeLevel, inputProvenance, dataFlow, metadata };
}
function assessmentFields(value) {
  const { actionId, score, reasons, decision, historyLength, effectiveSensitivity, sourceArtifactIds } = value;
  return { actionId, score, reasons, decision, historyLength, effectiveSensitivity, sourceArtifactIds };
}
export function buildSessionTrace({ mode, scenario, runId, sessionId, status, events, pending, observedAt }) {
  if (!["live-azure", "scripted-replay"].includes(mode)) throw new Error("Unknown trace mode");
  const live = mode === "live-azure";
  const rows = events.map(event => {
    const action = live ? event.action : event;
    const review = event.assessment.decision === "Review";
    return {
      action: actionFields(action),
      assessment: assessmentFields(event.assessment),
      executed: event.executed,
      approval: {
        source: review ? (live ? "human-review" : "scripted") : "not-required",
        outcome: !review ? "not-required" : event.executed ? "approved" : "not-approved",
        // The current API does not distinguish explicit rejection from expiry.
        approved: review && event.executed && (live ? event.approved === true : true)
      },
      ...(live && event.output !== undefined ? { syntheticToolOutput: event.output } : {}),
      ...(!live && event.pointAssessment ? { pointAssessment: assessmentFields(event.pointAssessment) } : {})
    };
  });
  return structuredClone({
    schemaVersion: "1.0",
    application: "Agent Flight Recorder",
    mode, scenario, runId, sessionId, status, observedAt,
    exportedAt: new Date().toISOString(),
    syntheticTools: true,
    snapshot: true,
    limitations: [
      "Unsigned runtime snapshot, not tamper-evident audit evidence.",
      "No private model reasoning or Azure configuration included.",
      "Approval timestamps and reviewer identity are not captured.",
      "Not-approved may mean rejection or expiry.",
      "Trace includes assessed events emitted by the loop; proposals rejected before assessment may be absent."
    ],
    counts: {
      assessed: rows.length + (pending ? 1 : 0),
      executed: rows.filter(e => e.executed).length,
      blocked: rows.filter(e => e.assessment.decision === "Block").length
    },
    events: rows,
    pending: pending ? {
      action: actionFields(pending.action),
      assessment: assessmentFields(pending.assessment),
      expiresAt: pending.expiresAt,
      executed: false,
      approval: { source: "human-review", outcome: "pending", approved: false }
    } : null
  });
}
export function downloadSessionTrace(trace) {
  const safeId = String(trace.sessionId || trace.runId || "session").replace(/[^a-zA-Z0-9_-]/g, "_");
  const url = URL.createObjectURL(new Blob([JSON.stringify(trace, null, 2)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "flight-recorder-" + trace.mode + "-" + safeId + "-" + Date.now() + ".json";
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
