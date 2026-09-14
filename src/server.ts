import { createServer } from "node:http";
import { ExecutionGate } from "./gate.js";
import { FlightRecorder } from "./engine.js";
import { demoActions } from "./scenario.js";

const server = createServer((request, response) => {
  if (request.url === "/api/demo") {
    const gate = new ExecutionGate(new FlightRecorder());
    const events = demoActions.map(action => {
      const approved = action.id !== "a5";
      const result = gate.evaluate(action, () => true, approved);
      return { ...action, assessment: result.assessment, executed: result.executed, approvalRequired: result.approvalRequired };
    });
    response.writeHead(200, { "Content-Type":"application/json", "Access-Control-Allow-Origin":"*" });
    response.end(JSON.stringify(events));
    return;
  }

  response.writeHead(404, { "Content-Type":"application/json" });
  response.end(JSON.stringify({ error:"Not found" }));
});

server.listen(3000, () => console.log("Agent Flight Recorder API listening on http://localhost:3000"));
