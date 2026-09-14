const $ = selector => document.querySelector(selector);
const labels = {
  running: "Azure is proposing the next action…",
  awaiting_approval: "Paused. Review the proposed action below.",
  model_stopped: "Model stopped. No further action proposed.",
  review_denied: "Review not approved. Action prevented; run ended.",
  policy_blocked: "Policy blocked a proposed action. Tool did not execute.",
  proposal_error: "Azure proposal failed. Check configuration or use the CLI diagnostic.",
  execution_or_approval_error: "Execution or approval failed. Run stopped.",
  repeated_action: "Run stopped because the model repeated an action.",
  precondition_failed: "Run stopped because a required earlier tool result was missing.",
  step_limit: "Run reached its model-call limit.",
  invalid_session: "Run stopped: invalid session.",
  run_error: "Run failed."
};
let runId = sessionStorage.getItem("flight-live-run");
let pendingId;
let timer;
let deciding = false;
let previousTrace = "";
const element = (tag, text, className) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
};
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {cache:"no-store"} : {
    method:"POST", headers:{"Content-Type":"application/json","X-Flight-Recorder":"dashboard"},
    body:JSON.stringify(body)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Request failed");
  return result;
}
function renderTrace(run) {
  const rows = run.events.map(event => ({...event, pending:false}));
  if (run.pending) rows.push({...run.pending, executed:false, approved:false, pending:true});
  const signature = JSON.stringify(rows);
  if (signature === previousTrace) return;
  previousTrace = signature;
  $("#live-chart").replaceChildren();
  $("#live-timeline").replaceChildren();
  rows.forEach((event, index) => {
    const {action, assessment} = event;
    const decisionClass = assessment.decision.toLowerCase();
    const bar = element("div", undefined, "bar-wrap");
    bar.append(element("span", String(assessment.score)));
    const fill = element("div", undefined, "bar " + decisionClass);
    fill.style.height = Math.max(assessment.score, 5) + "%";
    bar.append(fill, element("span", String(index + 1), "bar-label"));
    $("#live-chart").append(bar);
    const article = element("article", undefined, "event");
    article.append(element("div", String(index + 1), "marker " + decisionClass));
    const main = element("div", undefined, "event-main");
    main.append(element("div", action.tool + "." + action.operation, "event-title"));
    main.append(element("div", action.sensitivity + " · " + action.destinationTrust + " destination · " + action.id, "event-meta"));
    if (action.dataFlow) {
      main.append(element("div", "Inputs: " + (action.dataFlow.inputs.join(", ") || "source acquisition") +
        " · Outputs: " + (action.dataFlow.outputs.join(", ") || "none") +
        " · Effective sensitivity: " + (assessment.effectiveSensitivity || "unresolved"), "event-meta"));
    }
    const reasons = element("ul", undefined, "reasons");
    assessment.reasons.forEach(reason => reasons.append(element("li", reason)));
    main.append(reasons);
    if (event.output !== undefined) {
      const details = element("details");
      details.append(element("summary", "View synthetic tool output"), element("pre", JSON.stringify(event.output, null, 2)));
      main.append(details);
    }
    article.append(main);
    const status = element("div", undefined, "decision");
    status.append(element("b", assessment.decision, decisionClass), element("div", "Risk " + assessment.score + "/100", "score"),
      element("div", event.pending ? "AWAITING APPROVAL" : event.executed ? "EXECUTED" : "NOT EXECUTED", "execution " + (event.executed ? "" : "no")));
    if (event.approved) status.append(element("div", "Human approved", "score"));
    article.append(status);
    $("#live-timeline").append(article);
  });
}
function render(run) {
  $("#live-status").textContent = labels[run.status] || run.status;
  $("#live-session").textContent = run.sessionId || "Starting";
  $("#live-actions").textContent = run.events.length + (run.pending ? 1 : 0);
  $("#live-executed").textContent = run.events.filter(e => e.executed).length;
  $("#live-blocked").textContent = run.events.filter(e => e.assessment.decision === "Block").length;
  const active = ["running","awaiting_approval"].includes(run.status);
  $("#live-run").disabled = active;
  $("#live-scenario").disabled = active;
  $("#approval").hidden = !run.pending;
  if (pendingId !== run.pending?.action.id) $("#approval-error").textContent = "";
  pendingId = run.pending?.action.id;
  if (run.pending) {
    $("#approval-title").textContent = run.pending.action.tool + "." + run.pending.action.operation + " · risk " + run.pending.assessment.score;
    $("#approval-reasons").textContent = run.pending.assessment.reasons.join("; ");
    $("#approval-expiry").textContent = "Not executed. Approval expires at " + new Date(run.pending.expiresAt).toLocaleTimeString() + ".";
  }
  $("#approve").disabled = deciding;
  $("#reject").disabled = deciding;
  renderTrace(run);
  return active;
}
async function poll() {
  clearTimeout(timer);
  try {
    const run = await api("/api/live?id=" + encodeURIComponent(runId));
    $("#reconnect").hidden = true;
    if (render(run)) timer = setTimeout(poll, 700);
    else sessionStorage.removeItem("flight-live-run");
  } catch (error) {
    $("#live-status").textContent = error.message + ". If the server restarted, the in-memory run is gone.";
    $("#approval").hidden = true;
    $("#reconnect").hidden = false;
    $("#live-run").disabled = false;
    $("#live-scenario").disabled = false;
  }
}
$("#live-run").addEventListener("click", async () => {
  $("#live-run").disabled = true;
  $("#live-scenario").disabled = true;
  try {
    const result = await api("/api/live/start", {scenario:$("#live-scenario").value});
    clearTimeout(timer);
    runId = result.id;
    sessionStorage.setItem("flight-live-run", runId);
    previousTrace = "";
    $("#live-timeline").replaceChildren();
    $("#live-chart").replaceChildren();
    await poll();
  } catch (error) {
    $("#live-status").textContent = error.message;
    $("#live-run").disabled = false;
    $("#live-scenario").disabled = false;
  }
});
async function decide(approved) {
  if (!pendingId || deciding) return;
  deciding = true;
  $("#approve").disabled = $("#reject").disabled = true;
  try {
    await api("/api/live/approve", {id:runId, actionId:pendingId, approved});
  } catch (error) { $("#approval-error").textContent = error.message; }
  finally { deciding = false; await poll(); }
}
$("#approve").addEventListener("click", () => decide(true));
$("#reject").addEventListener("click", () => decide(false));
$("#reconnect").addEventListener("click", poll);
if (runId) poll();
