import { ActionEvent } from "./types.js";

const action = (id: string, sessionId: string, values: Omit<ActionEvent, "id" | "sessionId" | "timestamp">): ActionEvent => ({
  id, sessionId, timestamp: new Date().toISOString(), ...values
});

export const scenarios: Record<string, ActionEvent[]> = {
  safe: [
    action("s1", "safe-session", {tool:"file-reader",operation:"read",resourceType:"public_document",sensitivity:"Public",destinationTrust:"Trusted",privilegeLevel:1,inputProvenance:"System"}),
    action("s2", "safe-session", {tool:"calendar",operation:"create_event",resourceType:"calendar_entry",sensitivity:"Internal",destinationTrust:"Trusted",privilegeLevel:1,inputProvenance:"TrustedTool"}),
    action("s3", "safe-session", {tool:"notification",operation:"send",resourceType:"internal_message",sensitivity:"Internal",destinationTrust:"Trusted",privilegeLevel:1,inputProvenance:"TrustedTool"})
  ],
  suspicious: [
    action("p1", "suspicious-session", {tool:"file-reader",operation:"read",resourceType:"document",sensitivity:"Internal",destinationTrust:"Trusted",privilegeLevel:1,inputProvenance:"UntrustedDocument"}),
    action("p2", "suspicious-session", {tool:"records-api",operation:"query",resourceType:"customer_records",sensitivity:"Confidential",destinationTrust:"Trusted",privilegeLevel:3,inputProvenance:"TrustedTool"}),
    action("p3", "suspicious-session", {tool:"email",operation:"send",resourceType:"internal_message",sensitivity:"Confidential",destinationTrust:"Unknown",privilegeLevel:2,inputProvenance:"TrustedTool"})
  ],
  exfiltration: [
    action("a1", "demo-attack-001", {tool:"file-reader",operation:"read",resourceType:"document",sensitivity:"Internal",destinationTrust:"Trusted",privilegeLevel:1,inputProvenance:"UntrustedDocument",metadata:{name:"quarterly-review.txt"}}),
    action("a2", "demo-attack-001", {tool:"records-api",operation:"query",resourceType:"customer_records",sensitivity:"Restricted",destinationTrust:"Trusted",privilegeLevel:4,inputProvenance:"TrustedTool"}),
    action("a3", "demo-attack-001", {tool:"exporter",operation:"create_export",resourceType:"data_export",sensitivity:"Restricted",destinationTrust:"Trusted",privilegeLevel:4,inputProvenance:"TrustedTool"}),
    action("a4", "demo-attack-001", {tool:"network",operation:"connect",resourceType:"external_destination",sensitivity:"Public",destinationTrust:"Untrusted",privilegeLevel:1,inputProvenance:"TrustedTool",metadata:{host:"outside.example"}}),
    action("a5", "demo-attack-001", {tool:"network",operation:"upload",resourceType:"data_export",sensitivity:"Internal",destinationTrust:"Untrusted",privilegeLevel:1,inputProvenance:"TrustedTool",metadata:{host:"outside.example"}})
  ]
};
