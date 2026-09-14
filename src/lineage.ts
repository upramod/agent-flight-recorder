import type { ActionEvent, Sensitivity } from "./types.js";
const rank: Record<Sensitivity, number> = { Public: 0, Internal: 1, Confidential: 2, Restricted: 3 };
export interface Artifact {
  sensitivity: Sensitivity;
  untrusted: boolean;
  sources: string[];
}
export function resolveLineage(action: ActionEvent, artifacts: Map<string, Artifact>) {
  const flow = action.dataFlow!;
  if (!Array.isArray(flow.inputs) || !Array.isArray(flow.outputs) ||
      [...flow.inputs, ...flow.outputs].some(id => typeof id !== "string" || !id.trim()) ||
      new Set(flow.inputs).size !== flow.inputs.length || new Set(flow.outputs).size !== flow.outputs.length ||
      flow.outputs.some(id => artifacts.has(id) || flow.inputs.includes(id))) {
    throw new Error("Invalid or reused artifact identifier");
  }
  if ((action.operation === "upload" || action.operation === "create_export") && !flow.inputs.length) {
    throw new Error("Artifact inputs required");
  }
  if (action.operation === "create_export" && !flow.outputs.length) throw new Error("Export output required");
  if (action.operation === "upload" && flow.outputs.length) throw new Error("Upload cannot register artifacts");
  let sensitivity = action.sensitivity;
  let untrusted = action.inputProvenance === "UntrustedDocument";
  const sources = new Set<string>();
  for (const id of flow.inputs) {
    const source = artifacts.get(id);
    if (!source) throw new Error("Artifact has no successful producer in this session: " + id);
    if (rank[source.sensitivity] > rank[sensitivity]) sensitivity = source.sensitivity;
    untrusted ||= source.untrusted;
    sources.add(id);
    source.sources.forEach(parent => sources.add(parent));
  }
  return { sensitivity, untrusted, sources: [...sources] };
}
export function artifactsFromHistory(history: ActionEvent[]) {
  const artifacts = new Map<string, Artifact>();
  for (const event of history) {
    if (!event.dataFlow) continue;
    const artifact = resolveLineage(event, artifacts);
    for (const id of event.dataFlow.outputs) artifacts.set(id, artifact);
  }
  return artifacts;
}
