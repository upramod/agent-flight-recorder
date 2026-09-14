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
  // Set by trusted tool adapters, never by model output. IDs are session-local and immutable.
  dataFlow?: { inputs: string[]; outputs: string[] };
  metadata?: Record<string, string>;
}

export interface Assessment {
  actionId: string;
  score: number;
  reasons: string[];
  decision: Decision;
  historyLength: number;
  effectiveSensitivity?: Sensitivity;
  sourceArtifactIds?: string[];
}
