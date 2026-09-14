import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { join, extname } from "node:path";
import { ExecutionGate } from "./gate.js";
import { FlightRecorder } from "./engine.js";
import { scenarios } from "./scenario.js";
import { LiveSessions } from "./liveSessions.js";
const live = new LiveSessions();

const contentTypes: Record<string, string> = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "text/javascript"
};

const server = createServer(async (request, response) => {
  const host = request.headers.host;
  if (host !== "localhost:3000" && host !== "127.0.0.1:3000") {
    response.writeHead(403); response.end(); return;
  }
  response.setHeader("Cache-Control", "no-store");
  const requestUrl = new URL(request.url ?? "/", "http://localhost:3000");

  if (requestUrl.pathname.startsWith("/api/live")) {
    const send = (code: number, body: unknown) => {
      response.writeHead(code, { "Content-Type": "application/json" });
      response.end(JSON.stringify(body));
    };
    if (request.method === "GET") {
      const run = live.get(requestUrl.searchParams.get("id") ?? "");
      send(run ? 200 : 404, run ?? { error: "Run not found" });
      return;
    }
    if (request.method !== "POST") { send(405, { error: "Method not allowed" }); return; }
    if (request.headers.origin !== "http://" + host || request.headers["x-flight-recorder"] !== "dashboard") {
      send(403, { error: "Same-origin dashboard required" }); return;
    }
    try {
      let body = "";
      for await (const chunk of request) {
        body += chunk.toString();
        if (body.length > 2048) { send(413, { error: "Request too large" }); return; }
      }
      const data = JSON.parse(body);
      if (!data || typeof data !== "object") { send(400, { error: "Invalid request" }); return; }
      if (requestUrl.pathname === "/api/live/start") {
        if (data.scenario !== "safe" && data.scenario !== "injection") { send(400, { error: "Unknown scenario" }); return; }
        if (!["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_API_KEY"].every(key => process.env[key]?.trim())) {
          send(503, { error: "Azure configuration missing in the server terminal" }); return;
        }
        try { send(202, { id: live.start(data.scenario) }); }
        catch { send(409, { error: "A live run is already active. Return to its tab or wait for its approval to expire." }); }
      } else if (requestUrl.pathname === "/api/live/approve") {
        if (typeof data.id !== "string" || typeof data.actionId !== "string" || typeof data.approved !== "boolean") {
          send(400, { error: "Invalid approval" }); return;
        }
        const accepted = live.decide(data.id, data.actionId, data.approved);
        send(accepted ? 200 : 409, accepted ? { accepted: true } : { error: "Approval expired or already answered" });
      } else { send(404, { error: "Not found" }); }
    } catch { send(400, { error: "Invalid request" }); }
    return;
  }

  if (requestUrl.pathname === "/api/demo") {
    const scenarioName = requestUrl.searchParams.get("scenario") ?? "exfiltration";
    const selectedScenario = scenarios[scenarioName] ?? scenarios.exfiltration;
    const gate = new ExecutionGate(new FlightRecorder());
    const events = selectedScenario.map(action => {
      const approved = action.operation !== "upload";
      const result = gate.evaluate(action, () => true, approved);
      const pointAssessment = new FlightRecorder().assess(action);
      return { ...action, assessment: result.assessment, pointAssessment, executed: result.executed, approvalRequired: result.approvalRequired };
    });
    response.writeHead(200, { "Content-Type":"application/json" });
    response.end(JSON.stringify(events));
    return;
  }

  const requestedPath = requestUrl.pathname === "/" ? "index.html" : requestUrl.pathname.replace(/^\//, "");
  if (requestedPath && !requestedPath.includes("..")) {
    try {
      const body = await readFile(join(process.cwd(), "dashboard", requestedPath));
      response.writeHead(200, { "Content-Type": contentTypes[extname(requestedPath)] ?? "text/plain" });
      response.end(body);
      return;
    } catch {
      // Fall through to 404.
    }
  }

  response.writeHead(404, { "Content-Type":"application/json" });
  response.end(JSON.stringify({ error:"Not found" }));
});

server.listen(3000, "127.0.0.1", () => console.log("Agent Flight Recorder running at http://localhost:3000"));
