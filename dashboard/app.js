fetch("/api/demo").then(response => response.json()).then(events => {
  document.querySelector("#timeline").innerHTML = events.map((e, i) => {
    const a = e.assessment;
    return `<article class="event"><div class="marker ${a.decision.toLowerCase()}">${i+1}</div><div class="event-main"><div class="event-title">${e.tool}.<span>${e.operation}</span></div><div class="event-meta">${e.resourceType} · session event ${e.id}</div><ul class="reasons">${a.reasons.map(r => `<li>${r}</li>`).join("")}</ul></div><div class="decision"><b class="${a.decision.toLowerCase()}">${a.decision}</b><div class="score">risk score ${a.score}/100</div><div class="execution ${e.executed ? "" : "no"}">${e.executed ? "EXECUTED" : "NOT EXECUTED"}</div></div></article>`;
  }).join("");
}).catch(error => {
  document.querySelector("#timeline").innerHTML = `<p>API unavailable. Start the server with <code>npm start</code>.</p>`;
  console.error(error);
});
