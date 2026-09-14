const runButton = document.querySelector("#run-demo");

async function loadDemo() {
  runButton.disabled = true;
  runButton.textContent = "Running...";
  document.querySelector("#run-status").textContent = "Replaying trajectory...";
  const timeline = document.querySelector("#timeline");
  try {
    const events = await fetch("/api/demo?run=" + Date.now()).then(response => response.json());
    const assessments = events.map(e => e.assessment);
    document.querySelector("#session").textContent = events[0].sessionId;
    document.querySelector("#actions").textContent = events.length;
    document.querySelector("#executed").textContent = events.filter(e => e.executed).length;
    document.querySelector("#blocked").textContent = events.filter(e => e.assessment.decision === "Block").length;

    document.querySelector("#risk-chart").innerHTML = assessments.map((a, i) =>
      `<div class="bar-wrap"><span>${a.score}</span><div class="bar ${a.decision.toLowerCase()}" style="height:${Math.max(a.score, 5)}%"></div><span class="bar-label">a${i + 1}</span></div>`
    ).join("");

    document.querySelector("#run-status").textContent = "Demo completed at " + new Date().toLocaleTimeString();
    timeline.innerHTML = events.map((e, i) => {
      const a = e.assessment;
      return `<article class="event"><div class="marker ${a.decision.toLowerCase()}">${i+1}</div><div class="event-main"><div class="event-title">${e.tool}.<span>${e.operation}</span></div><div class="event-meta">${e.resourceType} · session event ${e.id}</div><ul class="reasons">${a.reasons.map(r => `<li>${r}</li>`).join("")}</ul></div><div class="decision"><b class="${a.decision.toLowerCase()}">${a.decision}</b><div class="score">risk score ${a.score}/100</div><div class="execution ${e.executed ? "" : "no"}">${e.executed ? "EXECUTED" : "NOT EXECUTED"}</div></div></article>`;
    }).join("");
  } catch (error) {
    document.querySelector("#run-status").textContent = "Unable to reach policy API";
    timeline.innerHTML = `<p>API unavailable. Start the server with <code>npm start</code>.</p>`;
    console.error(error);
  } finally {
    runButton.disabled = false;
    runButton.textContent = "Run attack demo";
  }
}

runButton.addEventListener("click", loadDemo);
loadDemo();
