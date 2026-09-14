const runButton = document.querySelector("#run-demo");
const scenarioSelect = document.querySelector("#scenario");
let replayId = 0;

const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

function renderEvent(e, i) {
  const a = e.assessment;
  return `<article class="event"><div class="marker ${a.decision.toLowerCase()}">${i + 1}</div><div class="event-main"><div class="event-title">${e.tool}.<span>${e.operation}</span></div><div class="event-meta">${e.resourceType} · session event ${e.id}</div><ul class="reasons">${a.reasons.map(r => `<li>${r}</li>`).join("")}</ul></div><div class="decision"><b class="${a.decision.toLowerCase()}">${a.decision}</b><div class="score">risk score ${a.score}/100</div><div class="execution ${e.executed ? "" : "no"}">${e.executed ? "EXECUTED" : "NOT EXECUTED"}</div></div></article>`;
}

async function loadDemo() {
  const currentReplay = ++replayId;
  runButton.disabled = true;
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
      document.querySelector("#risk-chart").insertAdjacentHTML("beforeend", `<div class="bar-wrap"><span>${a.score}</span><div class="bar ${a.decision.toLowerCase()}" style="height:${Math.max(a.score, 5)}%"></div><span class="bar-label">a${i + 1}</span></div>`);
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
    document.querySelector("#run-status").textContent = "Demo completed at " + new Date().toLocaleTimeString();
  } catch (error) {
    document.querySelector("#run-status").textContent = "Unable to reach policy API";
    timeline.innerHTML = `<p>API unavailable. Start the server with <code>npm start</code>.</p>`;
    console.error(error);
  } finally {
    if (currentReplay === replayId) {
      runButton.disabled = false;
      runButton.textContent = "Run scenario";
    }
  }
}

runButton.addEventListener("click", loadDemo);
loadDemo();
