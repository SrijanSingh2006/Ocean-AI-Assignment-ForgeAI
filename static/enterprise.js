"use strict";

const engineering = (() => {
  const labels = {
    conflicts: "Source conflicts", traces: "Execution traces", security: "Security checks",
    models: "Model comparison", languages: "Language evaluation", feedback: "Feedback review",
    impact: "Document impact", releases: "Releases and export", calibration: "Confidence calibration",
  };
  const reports = new Map();
  let kind = "conflicts";
  let dashboardData;
  let dashboardError;
  let dashboardPending = false;
  let extra = null;
  let viewRun;

  function clear() {
    reports.clear();
    kind = "conflicts";
    dashboardData = dashboardError = undefined;
    dashboardPending = false;
    extra = null;
    viewRun = undefined;
  }

  function open(id) {
    if (viewRun !== id) {
      extra = null;
      kind = "conflicts";
      viewRun = id;
    }
    fetchPanel(id);
  }

  const path = (id, endpoint = kind) => `/api/runs/${encodeURIComponent(id)}/${endpoint}`;
  const canEdit = () => state.session?.role === "admin";
  const form = (op, body, action, more = "") =>
    `<form class="lab-form" data-engineering-form="${esc(op)}" ${more}>${body}<button class="btn primary small" type="submit">${esc(action)}</button></form>`;
  const input = (name, label, options = "") =>
    `<label class="field"><span class="field-label">${esc(label)}</span><input name="${name}" type="text" ${options}></label>`;
  const table = (rows) => `<ul class="list">${rows.map((line) => `<li>${line}</li>`).join("")}</ul>`;
  const empty = (text) => `<p class="muted">${esc(text)}</p>`;
  const show = (data) => data ? jsonBlock(data) : empty("Run this analysis to view a report.");
  const record = (id) => reports.get(`${id}:${kind}`);

  async function fetchPanel(id, endpoint = kind) {
    const key = `${id}:${endpoint}`;
    if (endpoint === "calibration") return;
    if (reports.get(key)?.pending) return;
    const entry = {pending: true};
    reports.set(key, entry);
    draw(id);
    try {
      entry.value = await api(path(id, endpoint));
    } catch (error) {
      entry.error = error.message;
    }
    entry.pending = false;
    draw(id);
  }

  function draw(id) {
    if (state.location === "run" && state.runScreen === id && state.tab === "engineering") render();
  }

  function dashboard() {
    const d = dashboardData;
    if (dashboardError) return `<section class="card sheet info bad" role="alert">${esc(dashboardError)}</section>`;
    if (!d) return '<div class="card sheet"><span class="spinner" aria-hidden="true"></span> Loading workspace metrics</div>';
    const reviewer = state.session?.review_demo;
    const values = [
      [reviewer ? "Sample agents" : "Generated agents", d.generated_agents], ["Evaluation cases", d.evaluation_cases],
      [reviewer ? "Average sample score" : "Average score", d.average_score === null ? "—" : `${d.average_score}%`],
      [reviewer ? "Grounding checks passed" : "Grounded responses", d.grounding_rate === null ? "—" : `${Math.round(d.grounding_rate * 100)}%`],
    ];
    if (!reviewer) values.push(
      ["Security checks", d.security_checks], ["Regression failures", d.regression_failures],
      ["Pending approvals", d.pending_approvals], ["Pending feedback", d.pending_feedback],
    );
    const summary = reviewer
      ? `Scores from the recorded evaluations of ${d.recorded_samples} bundled sample agents.`
      : `Metrics from your builds. ${d.recorded_samples} recorded samples are listed separately.`;
    const reports = reviewer
      ? `<section class="card sheet">${section("history", "Sample runs")}
        ${runHistoryRows(d.recent) || empty("Sample runs are unavailable.")}</section>`
      : `<section class="card sheet">${section("history", "Recent builds")}
        ${d.recent.length ? table(d.recent.map((row) => `<a href="#run/${esc(row.id)}">${esc(row.name)}</a> · ${esc(titleFor(row.status))}`)) : empty("Workspace builds will appear here.")}</section>
        <section class="card sheet">${section("target", "Recent evaluation failures")}
        ${d.recent_failures.length ? table(d.recent_failures.map((row) => `${esc(row.case)} · ${esc(row.failure)}`)) : empty("No failed evaluation cases in the recorded workspace builds.")}</section>`;
    return `<div class="screen"><div class="page-heading"><div><h1>${reviewer ? "Reviewer dashboard" : "Workspace overview"}</h1>
      <p>${esc(summary)}</p></div>
      ${canEdit() ? '<a class="btn primary" href="#build">New agent</a>' : ""}</div>
      <div class="panel-grid">${values.map(([label, value]) => `<div class="card metric"><small>${label}</small><strong>${esc(value)}</strong></div>`).join("")}</div>
      ${reports}</div>`;
  }

  async function loadDashboard() {
    if (dashboardPending) return;
    const session = state.session;
    dashboardPending = true;
    try {
      const data = await api("/api/dashboard");
      if (state.session === session) {
        dashboardData = data;
        dashboardError = null;
      }
    } catch (error) {
      if (state.session === session) dashboardError = error.message;
    } finally {
      if (state.session === session) {
        dashboardPending = false;
        if (state.location === "dashboard") render();
      }
    }
  }

  function displayConflicts(data) {
    if (!data.conflicts.length) return empty("No comparable policy disagreements were detected.");
    return data.conflicts.map((entry) => {
      const selection = data.selections[entry.id];
      const regression = data.regression_cases?.[entry.id];
      return `<article class="lab-card"><h3>${esc(entry.topic)} ${badge(selection ? "Resolved" : "Needs review", selection ? "good" : "warn")}</h3>
        ${regression ? badge(regression.verified ? "Verified regression case" : "Regression case needs review") : ""}
        <p class="muted">${esc(entry.type.replaceAll("_", " "))}${entry.basis ? " · " + esc(entry.basis) : ""}</p>
        <div class="lab-claims">${entry.claims.map((claim) => `<div><strong>${esc(claim.document)}</strong>
          <p>${esc(claim.statement)}</p><small>${esc(claim.locator)} ${claim.version_hint ? " · " + esc(claim.version_hint) : ""}</small></div>`).join("")}</div>
        ${canEdit() && !data.active_version ? form("resolve",
          `<label class="field"><span class="field-label">Applicable source</span><select name="passage_id">${entry.claims.map((claim) =>
            `<option value="${esc(claim.passage_id)}" ${claim.passage_id === selection ? "selected" : ""}>${esc(claim.document)} · ${esc(claim.value)} ${esc(claim.unit)}</option>`).join("")}</select></label>` +
          input("reason", "Reason for selection", 'required maxlength="500"'), "Save resolution", `data-id="${esc(entry.id)}"`) : ""}</article>`;
    }).join("") + (data.history.length ? `<details><summary>Resolution history</summary>${jsonBlock(data.history)}</details>` : "");
  }

  function displayTraces(data) {
    const rows = data.map((row) => `<div class="lab-row"><div><strong>${esc(row.question)}</strong>
      <p class="muted">${esc(row.at)} · ${esc(titleFor(row.status))}</p></div>
      <button class="btn small" data-trace="${esc(row.id)}">Open timeline</button>
      ${canEdit() ? `<button class="btn small" data-remove-trace="${esc(row.id)}">Delete</button>` : ""}</div>`);
    let timeline = "";
    if (extra?.events) {
      timeline = `<article class="lab-card"><h3>Trace ${esc(extra.id)}</h3>
        <ol class="timeline">${extra.events.map((event) => `<li><strong>${esc(event.stage.replaceAll("_", " "))}</strong>
          ${badge(`${event.elapsed_ms} ms`)}${jsonBlock(Object.fromEntries(Object.entries(event).filter(([key]) => !["stage", "elapsed_ms"].includes(key))))}</li>`).join("")}</ol>
        <p>${esc(extra.answer)}</p></article>`;
    }
    return (rows.length ? rows.join("") : empty("Ask a question in Agent chat to record a trace.")) + timeline;
  }

  function displayFeedback(data) {
    if (!data.length) return empty("Submitted chat feedback appears here for review.");
    return data.map((row) => `<article class="lab-card"><h3>${esc(row.category.replaceAll("_", " "))} ${badge(row.state)}</h3>
      <p>${esc(row.question)}</p><p class="muted">${esc(row.comment)}</p>
      ${row.response?.citations?.length ? table(row.response.citations.map((citation) =>
        `${esc(citation.passage_id)} · ${esc(citation.document)}`)) : ""}
      ${canEdit() && row.state === "pending" ? form("review-feedback",
        '<label class="field"><span class="field-label">Decision</span><select name="approve"><option value="true">Approve case</option><option value="false">Reject feedback</option></select></label>' +
        '<label class="field"><span class="field-label">Expected status</span><select name="expected_status"><option>answered</option><option>refused</option><option>clarify</option></select></label>' +
        input("anchors", "Passage IDs separated by commas") +
        '<label class="field"><span class="field-label">Suite</span><select name="suite"><option>regression</option><option>development</option></select></label>',
        "Record review", `data-id="${esc(row.id)}"`) : ""}</article>`).join("") + (extra ? show(extra) : "");
  }

  function displayImpact(data) {
    const request = canEdit() ? form("impact", input("previous_run_id", "Previous run ID", "required") +
      '<label class="switch-row"><input type="checkbox" name="full_regression"><span>Run full regression too</span></label>',
      "Analyze document changes") : "";
    if (!data.graph) return request + empty("Choose a prior build to compare its sources with this run.");
    const names = Object.fromEntries(data.graph.nodes.map((node) =>
      [node.id, node.label || node.document || node.section || node.case_id || node.kind || node.id]));
    const arcs = data.graph.edges.slice(0, 60).map((edge) =>
      `<li><span>${esc(names[edge.source] || edge.source)}</span><small>${esc(edge.relation.replaceAll("_", " "))}</small>
        <strong>${esc(names[edge.target] || edge.target)}</strong></li>`);
    return request + `<figure class="impact-flow"><figcaption>${data.graph.edges.length} verified links</figcaption>
      <ol>${arcs.join("")}</ol></figure><details><summary>Full impact and regression report</summary>${show(data)}</details>`;
  }

  function displayReleases(data, runId) {
    const versions = data.versions;
    const canApprove = canEdit() || state.session.can_approve;
    return `<div class="actions"><a class="btn primary small" href="${path(runId, "deployment")}">Export runnable agent</a></div>
      ${canEdit() ? form("release", input("source_run_id", "Source run ID", 'placeholder="Current run"') +
        input("label", "Release name", 'placeholder="Optional" maxlength="80"'), "Create release snapshot") : ""}
      ${versions.length ? versions.map((item) => `<div class="lab-row"><div><strong>${item.label ? esc(item.label) + " · " : ""}Version ${esc(item.number)}</strong>
        <p class="muted">${esc(item.id)} · ${esc(item.state)} ${item.active ? "· Active" : ""}</p></div>
        ${item.state === "pending" && canApprove ? `<button class="btn small" data-release-op="approve" data-id="${esc(item.id)}">Approve</button>` : ""}
        ${canEdit() && item.state === "approved" && !item.active ? `<button class="btn small" data-release-op="activate" data-id="${esc(item.id)}">Activate</button>
          <button class="btn small" data-release-op="rollback" data-id="${esc(item.id)}">Roll back to this version</button>` : ""}</div>`).join("") : empty("Create a release when the definition and sources are ready to freeze.")}
      ${versions.length > 1 ? form("release-diff", input("before", "Earlier version ID", "required") +
        input("after", "Later version ID", "required"), "Compare versions") : ""}
      ${extra ? show(extra) : ""}<details><summary>Release audit history</summary>${jsonBlock(data.history)}</details>`;
  }

  function displayModels(data) {
    if (!data.models.length) return empty("Configure model providers to run a comparison.");
    const percent = (value) => value == null ? "—" : `${Math.round(value * 100)}%`;
    return `<p>${data.recommended ? `Recommended model · ${esc(data.recommended)}` : "No model qualified for recommendation."}</p>
      <div class="lab-table-wrap"><table class="lab-table"><thead><tr>
        <th scope="col">Model</th><th scope="col">Score</th><th scope="col">Grounding</th><th scope="col">Correctness</th>
        <th scope="col">Refusal</th><th scope="col">Seconds</th><th scope="col">Tokens</th><th scope="col">Cost</th>
      </tr></thead><tbody>${data.models.map((entry) => `<tr><th scope="row">${esc(entry.id)}<small>${esc(entry.model)}</small>
        ${entry.status === "scored" ? badge(entry.model_used ? (entry.qualifies ? "Qualified" : "Below threshold") : "Fallback only") : badge(titleFor(entry.status))}</th>
        <td>${entry.scorecard ? `${esc(entry.scorecard.score)}%` : "—"}</td><td>${percent(entry.grounding)}</td>
        <td>${percent(entry.correctness)}</td><td>${percent(entry.refusal_accuracy)}</td><td>${esc(entry.elapsed_seconds)}</td>
        <td>${esc(entry.tokens ?? "—")}</td><td>${entry.cost == null ? "—" : `$${esc(entry.cost)}`}</td></tr>`).join("")}</tbody></table></div>`;
  }

  function displayLanguages(data) {
    const names = {en: "English", hi: "Hindi", ta: "Tamil", "hi-Latn": "Romanized Hindi",
      "ta-Latn": "Romanized Tamil", "hi-en": "Hindi–English", "ta-en": "Tamil–English"};
    const groups = Object.entries(data.languages);
    return `<div class="panel-grid">${Object.entries(data.languages).map(([code, entry]) =>
      `<div class="lab-card"><h3>${names[code] || esc(code)}</h3><strong>${entry.passed} passed · ${entry.scored}/${entry.total} scored</strong></div>`).join("")}</div>
      ${data.review ? `<p class="muted">${esc(data.review)}</p>` : ""}
      <div data-language-report><label class="field"><span class="field-label">Filter by language</span>
        <select data-language-filter><option value="">All languages</option>
          ${groups.map(([code]) => `<option value="${esc(code)}">${names[code] || esc(code)}</option>`).join("")}
        </select></label>
      ${data.results.map((entry) => `<article class="lab-card" data-case-language="${esc(entry.language)}"><h3>${names[entry.language] || esc(entry.language)} · ${esc(entry.case_id)}
        ${badge(entry.status === "scored" ? (entry.passed ? "Passed" : "Failed") : entry.status.replaceAll("_", " "), entry.passed ? "good" : "warn")}</h3>
        ${entry.question ? `<p><strong>${esc(entry.question)}</strong></p>` : ""}
        ${entry.response ? `<p lang="${esc(entry.response.language || "en")}">${esc(entry.response.answer)}</p>
          ${entry.response.citations.map((citation) => `<details><summary>${esc(citation.document)} · ${esc(citation.locator)}</summary>
            <blockquote>${esc(citation.quote)}</blockquote></details>`).join("")}` : ""}</article>`).join("")}</div>`;
  }

  document.addEventListener("change", (event) => {
    const select = event.target.closest("[data-language-filter]");
    if (!select) return;
    for (const row of select.closest("[data-language-report]").querySelectorAll("[data-case-language]")) {
      row.hidden = Boolean(select.value && select.value !== row.dataset.caseLanguage);
    }
  });

  function evidence(run) {
    const entry = record(run.id);
    let body;
    if (kind === "calibration") {
      body = canEdit() ? form("calibration",
        '<label class="field"><span class="field-label">Training cases as JSON</span><textarea name="training" required></textarea></label>' +
        '<label class="field"><span class="field-label">Disjoint validation cases as JSON</span><textarea name="validation" required></textarea></label>',
        "Measure calibration") + (extra ? show(extra) : "") : empty("An admin can evaluate labeled confidence datasets.");
    } else if (entry?.error) {
      body = `<p class="info bad" role="alert">${esc(entry.error)}</p><button class="btn small" data-lab-panel="${kind}">Retry</button>`;
    } else if (!entry || entry.pending) {
      body = '<p role="status"><span class="spinner" aria-hidden="true"></span> Loading report</p>';
    } else {
      const data = entry.value;
      if (kind === "conflicts") body = displayConflicts(data);
      else if (kind === "traces") body = displayTraces(data);
      else if (kind === "feedback") body = displayFeedback(data);
      else if (kind === "impact") body = displayImpact(data);
      else if (kind === "releases") body = displayReleases(data, run.id);
      else if (kind === "security") {
        body = (canEdit() ? form("security", "", "Run conformance checks") : "") +
          (data.checks?.length ? table(data.checks.map((check) => `${badge(check.status === "not_applicable" ? "Not applicable" : check.passed ? "Passed" : "Failed", check.passed ? "good" : "")} ${esc(check.name)}`)) : empty("Run the fixed defensive checks against this agent.")) +
          (data.source_findings?.length ? `<details><summary>Instruction-like source passages</summary>${show(data.source_findings)}</details>` : "");
      } else if (kind === "models") {
        body = (canEdit() ? form("models", '<label class="field"><span class="field-label">Minimum score</span><input name="minimum_score" type="number" min="0" max="100" value="80" required></label>', "Benchmark configured models") : "") +
          (data.models ? displayModels(data) : empty("Compare providers on the same development suite."));
      } else {
        body = (canEdit() ? form("languages", "", "Evaluate supported languages") : "") +
          (data.languages ? displayLanguages(data) : empty("Check verified responses, refusals, and unavailable languages separately."));
      }
    }
    return `<section class="card sheet">${section("wrench", "Engineering lab")}
      <div class="tabs lab-tabs" aria-label="Engineering workflows">${Object.entries(labels).map(([key, label]) =>
        `<button class="tab ${key === kind ? "active" : ""}" aria-pressed="${kind === key}" data-lab-panel="${key}">${label}</button>`).join("")}</div>
      <h3>${labels[kind]}</h3><div class="lab-content">${body}</div></section>`;
  }

  async function mutate(id, endpoint, body, method = "POST") {
    return api(path(id, endpoint), {
      method, headers: {"Content-Type": "application/json"}, body: body === undefined ? undefined : JSON.stringify(body),
    });
  }

  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-lab-panel], [data-trace], [data-remove-trace], [data-release-op]");
    if (!button || state.location !== "run" || state.tab !== "engineering" || !state.runScreen) return;
    const id = state.runScreen;
    const data = button.dataset;
    try {
      if (data.labPanel) {
        kind = data.labPanel;
        extra = null;
        await fetchPanel(id);
        draw(id);
      } else if (data.trace) {
        const trace = await api(path(id, `traces/${encodeURIComponent(data.trace)}`));
        if (viewRun !== id || kind !== "traces") return;
        extra = trace;
        draw(id);
      } else if (data.removeTrace && window.confirm("Delete this trace?")) {
        await mutate(id, `traces/${encodeURIComponent(data.removeTrace)}`, undefined, "DELETE");
        extra = null;
        await fetchPanel(id);
      } else if (data.releaseOp) {
        await mutate(id, `releases/${encodeURIComponent(data.id)}/${data.releaseOp}`);
        await fetchPanel(id);
        toast("Release updated");
      }
    } catch (error) {
      toast(error.message);
    }
  });

  document.addEventListener("submit", async (event) => {
    const target = event.target;
    if (!target.dataset.engineeringForm && !target.dataset.feedbackTrace) return;
    event.preventDefault();
    const button = target.querySelector('button[type="submit"]');
    button.disabled = true;
    const values = new FormData(target);
    const op = target.dataset.engineeringForm;
    const id = state.runScreen;
    const panel = kind;
    const session = state.session;
    const setExtra = (value) => {
      if (state.session === session && viewRun === id && kind === panel) extra = value;
    };
    try {
      if (target.dataset.feedbackTrace) {
        await mutate(target.dataset.runId, "feedback", {trace_id: target.dataset.feedbackTrace,
          category: values.get("category"), comment: values.get("comment")});
        target.hidden = true;
        toast("Feedback added to the review queue");
        return;
      }
      if (op === "resolve") await mutate(id, `conflicts/${encodeURIComponent(target.dataset.id)}`,
        {passage_id: values.get("passage_id"), reason: values.get("reason")});
      else if (op === "review-feedback") setExtra(await mutate(id, `feedback/${encodeURIComponent(target.dataset.id)}/review`, {
        approve: values.get("approve") === "true", expected_status: values.get("expected_status"),
        anchors: values.get("anchors").split(",").map((value) => value.trim()).filter(Boolean), suite: values.get("suite"),
      }));
      else if (op === "release") await mutate(id, "releases", {source_run_id: values.get("source_run_id") || null,
        label: values.get("label").trim() || null});
      else if (op === "release-diff") setExtra(await api(path(id, "release-diff?" + new URLSearchParams(values))));
      else if (op === "impact") await mutate(id, "impact", {
        previous_run_id: values.get("previous_run_id"), full_regression: values.get("full_regression") !== null,
      });
      else if (op === "models") await mutate(id, "models", {minimum_score: Number(values.get("minimum_score"))});
      else if (op === "calibration") setExtra(await api("/api/confidence/calibration", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({training: JSON.parse(values.get("training")), validation: JSON.parse(values.get("validation"))}),
      }));
      else await mutate(id, op);
      if (state.session !== session) return;
      await fetchPanel(id, panel);
      draw(id);
      toast("Workspace report updated");
    } catch (error) {
      toast(error.message);
    } finally {
      button.disabled = false;
    }
  });

  return {dashboard, loadDashboard, evidence, open, clear, displayLanguages};
})();
