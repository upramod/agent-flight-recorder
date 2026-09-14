const runButton = document.querySelector("#run-demo");
const scenarioSelect = document.querySelector("#scenario");
let replayId = 0;

function setReplayState(label, state) {
  document.querySelector("#replay-state-label").textContent = label;
  document.querySelector("#replay-state").dataset.state = state;
}

function appendRiskBar(event) {
  const wrap = document.createElement("div");
  wrap.className = "replay-bar-wrap";
  const track = document.createElement("div");
  track.className = "replay-bar-track";
  const score = Math.max(0, Math.min(100, event.assessment.score));
  const fill = document.createElement("div");
  fill.className = "replay-bar-fill " + event.assessment.decision.toLowerCase();
  fill.style.height = score + "%";
  if (score === 0) fill.classList.add("zero-score");
  const value = document.createElement("span");
  value.className = "replay-bar-value";
  value.textContent = String(score);
  value.style.bottom = score + "%";
  track.append(fill, value);
  const label = document.createElement("span");
  label.className = "bar-label";
  label.textContent = event.id;
  wrap.setAttribute("aria-label", event.id + ": risk " + score + " out of 100");
  wrap.append(track, label);
  document.querySelector("#risk-chart").append(wrap);
}

const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

function renderEvent(e, i) {
  const a = e.assessment;
  return `<article class="event"><div class="marker ${a.decision.toLowerCase()}">${i + 1}</div><div class="event-main"><div class="event-title">${e.tool}.<span>${e.operation}</span></div><div class="event-meta">${e.resourceType} · session event ${e.id}</div><ul class="reasons">${a.reasons.map(r => `<li>${r}</li>`).join("")}</ul></div><div class="decision"><b class="${a.decision.toLowerCase()}">${a.decision}</b><div class="score">risk score ${a.score}/100</div><div class="execution ${e.executed ? "" : "no"}">${e.executed ? "EXECUTED" : "NOT EXECUTED"}</div></div></article>`;
}

function renderArtifactComparison(events) {
  const body = document.querySelector("#artifact-rows");
  body.replaceChildren();
  const producers = new Map();
  for (const event of events) {
    if (event.executed) {
      for (const id of event.dataFlow?.outputs ?? []) producers.set(id, event);
    }
    if (event.operation !== "upload" || !event.dataFlow) continue;
    for (const artifactId of event.dataFlow.inputs) {
      const producer = producers.get(artifactId);
      const sources = producer?.dataFlow?.inputs ?? [];
      const row = document.createElement("tr");
      const values = [
        sources.length ? sources.join(", ") : "Source unresolved",
        artifactId,
        event.assessment.effectiveSensitivity ?? "Unresolved",
        event.destinationTrust,
        event.assessment.decision + " · " + event.assessment.score + "/100",
        event.executed ? "Executed" : "Not executed"
      ];
      values.forEach((value, index) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        if (index === 4) cell.className = event.assessment.decision.toLowerCase();
        row.append(cell);
      });
      body.append(row);
    }
  }
}

async function loadDemo() {
  const currentReplay = ++replayId;
  setReplayState("Replaying…", "running");
  runButton.disabled = true;
  scenarioSelect.disabled = true;
  document.querySelector("#comparison").hidden = true;
  document.querySelector("#artifact-comparison").hidden = true;
  document.querySelector("#artifact-rows").replaceChildren();
  runButton.textContent = "Running " + scenarioSelect.options[scenarioSelect.selectedIndex].text + "...";
  document.querySelector("#run-status").textContent = "Replaying trajectory...";
  const timeline = document.querySelector("#timeline");
  timeline.innerHTML = "";
  document.querySelector("#risk-chart").innerHTML = "";

  try {
    const events = await fetch("/api/demo?scenario=" + scenarioSelect.value + "&run=" + Date.now()).then(response => {
      if (!response.ok) throw new Error("Policy API returned " + response.status);
      return response.json();
    });
    if (currentReplay !== replayId) return;

    const assessments = events.map(e => e.assessment);
    document.querySelector("#session").textContent = events[0].sessionId;
    document.querySelector("#actions").textContent = events.length;
    document.querySelector("#executed").textContent = events.filter(e => e.executed).length;
    document.querySelector("#blocked").textContent = events.filter(e => e.assessment.decision === "Block").length;

    const finalEvent = events[events.length - 1];
    document.querySelector("#point-decision").textContent = finalEvent.pointAssessment.decision;
    document.querySelector("#point-score").textContent = "risk score " + finalEvent.pointAssessment.score + "/100";
    document.querySelector("#trajectory-decision").textContent = finalEvent.assessment.decision;
    document.querySelector("#trajectory-score").textContent = "risk score " + finalEvent.assessment.score + "/100";

    for (let i = 0; i < events.length; i++) {
      if (currentReplay !== replayId) return;
      const e = events[i];
      const a = assessments[i];
      appendRiskBar(e);
      timeline.insertAdjacentHTML("beforeend", renderEvent(e, i));
      const newest = timeline.lastElementChild;
      newest.style.opacity = "0";
      newest.style.transform = "translateY(8px)";
      requestAnimationFrame(() => {
        newest.style.transition = "opacity .35s ease, transform .35s ease";
        newest.style.opacity = "1";
        newest.style.transform = "translateY(0)";
      });
      await wait(450);
    }
    if (events.some(event => event.dataFlow)) {
      renderArtifactComparison(events);
      document.querySelector("#artifact-comparison").hidden = false;
    } else {
      document.querySelector("#comparison").hidden = false;
    }
    setReplayState("Replay complete", "complete");
    document.querySelector("#run-status").textContent = "Demo completed at " + new Date().toLocaleTimeString();
  } catch (error) {
    setReplayState("Replay failed", "failed");
    document.querySelector("#run-status").textContent = "Unable to reach policy API";
    timeline.innerHTML = `<p>API unavailable. Start the server with <code>npm start</code>.</p>`;
    console.error(error);
  } finally {
    if (currentReplay === replayId) {
      runButton.disabled = false;
      scenarioSelect.disabled = false;
      runButton.textContent = "Run scenario";
    }
  }
}

runButton.addEventListener("click", loadDemo);
loadDemo();
