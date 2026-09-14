import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { join, extname } from "node:path";
import { ExecutionGate } from "./gate.js";
import { FlightRecorder } from "./engine.js";
import { demoActions } from "./scenario.js";

const contentTypes: Record<string, string> = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "text/javascript"
};

const server = createServer(async (request, response) => {
  if (request.url === "/api/demo") {
    const gate = new ExecutionGate(new FlightRecorder());
    const events = demoActions.map(action => {
      const approved = action.id !== "a5";
      const result = gate.evaluate(action, () => true, approved);
      return { ...action, assessment: result.assessment, executed: result.executed, approvalRequired: result.approvalRequired };
    });
    response.writeHead(200, { "Content-Type":"application/json" });
    response.end(JSON.stringify(events));
    return;
  }

  const requestedPath = request.url === "/" ? "index.html" : request.url?.replace(/^\//, "");
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
