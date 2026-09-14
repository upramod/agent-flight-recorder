export type Decision = "Allow" | "Review" | "Block";
export type Sensitivity = "Public" | "Internal" | "Confidential" | "Restricted";
export type Trust = "Trusted" | "Unknown" | "Untrusted";
export type Provenance = "System" | "User" | "TrustedTool" | "UntrustedDocument" | "External";

export interface ActionEvent {
  id: string;
  sessionId: string;
  timestamp: string;
  tool: string;
  operation: string;
  resourceType: string;
  sensitivity: Sensitivity;
  destinationTrust: Trust;
  privilegeLevel: number;
  inputProvenance: Provenance;
  metadata?: Record<string, string>;
}

export interface Assessment {
  actionId: string;
  score: number;
  reasons: string[];
  decision: Decision;
  historyLength: number;
}
