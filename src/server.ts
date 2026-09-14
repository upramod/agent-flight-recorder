import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { join, extname } from "node:path";
import { ExecutionGate } from "./gate.js";
import { FlightRecorder } from "./engine.js";
import { scenarios } from "./scenario.js";

const contentTypes: Record<string, string> = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "text/javascript"
};

const server = createServer(async (request, response) => {
  const requestUrl = new URL(request.url ?? "/", "http://localhost:3000");

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

server.listen(3000, () => console.log("Agent Flight Recorder running at http://localhost:3000"));
