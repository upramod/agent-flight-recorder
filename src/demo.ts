import { FlightRecorder } from "./engine.js";
import { ExecutionGate } from "./gate.js";
import { ActionEvent } from "./types.js";

const sessionId = "demo-attack-001";
const base = {
  sessionId,
  timestamp: new Date().toISOString(),
  privilegeLevel: 1
};

const actions: ActionEvent[] = [
  {
    ...base,
    id: "a1",
    tool: "file-reader",
    operation: "read",
    resourceType: "document",
    sensitivity: "Internal",
    destinationTrust: "Trusted",
    privilegeLevel: 1,
    inputProvenance: "UntrustedDocument",
    metadata: { name: "quarterly-review.txt" }
  },
  {
    ...base,
    id: "a2",
    tool: "records-api",
    operation: "query",
    resourceType: "customer_records",
    sensitivity: "Restricted",
    destinationTrust: "Trusted",
    privilegeLevel: 4,
    inputProvenance: "TrustedTool"
  },
  {
    ...base,
    id: "a3",
    tool: "exporter",
    operation: "create_export",
    resourceType: "data_export",
    sensitivity: "Restricted",
    destinationTrust: "Trusted",
    privilegeLevel: 4,
    inputProvenance: "TrustedTool"
  },
  {
    ...base,
    id: "a4",
    tool: "network",
    operation: "connect",
    resourceType: "external_destination",
    sensitivity: "Public",
    destinationTrust: "Untrusted",
    privilegeLevel: 1,
    inputProvenance: "TrustedTool",
    metadata: { host: "outside.example" }
  },
  {
    ...base,
    id: "a5",
    tool: "network",
    operation: "upload",
    resourceType: "data_export",
    sensitivity: "Restricted",
    destinationTrust: "Untrusted",
    privilegeLevel: 4,
    inputProvenance: "TrustedTool",
    metadata: { host: "outside.example" }
  }
];

const gate = new ExecutionGate(new FlightRecorder());

console.log("Agent Flight Recorder: trajectory demo");
for (const action of actions) {
  const result = gate.evaluate(action, currentAction => {
    return `EXECUTED ${currentAction.tool}.${currentAction.operation}`;
  });

  console.log(
    `[${result.assessment.decision.padEnd(6)}] ${action.id} ${action.tool}.${action.operation} score=${result.assessment.score} executed=${result.executed}`
  );
  for (const reason of result.assessment.reasons) {
    console.log(`         - ${reason}`);
  }
  if (result.approvalRequired) {
    console.log("         - approval required before execution");
  }
}
