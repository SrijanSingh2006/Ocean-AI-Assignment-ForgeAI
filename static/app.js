"use strict";

const icons = {
  layers: '<path d="m12 2 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 17l9 5 9-5"/>',
  wand: '<path d="m15 4 5 5M4 20l12-12m-9 2 2 2m10 3v5m-2.5-2.5h5M5 3v4M3 5h4M19 2v3m-1.5-1.5h3"/>',
  history: '<path d="M3 12a9 9 0 1 0 2.5-6.2L3 8m0-5v5h5m4-1v5l3 2"/>',
  message: '<path d="M20 15a2 2 0 0 1-2 2H8l-4 4V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2zM8 8h8m-8 4h5"/>',
  box: '<path d="M21 8v8a2 2 0 0 1-1 1.7l-7 4a2 2 0 0 1-2 0l-7-4A2 2 0 0 1 3 16V8a2 2 0 0 1 1-1.7l7-4a2 2 0 0 1 2 0l7 4A2 2 0 0 1 21 8ZM3.3 7l8.7 5 8.7-5M12 22V12m-5-7 10 6"/>',
  cpu: '<rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M9 2v3m6-3v3M9 19v3m6-3v3M2 9h3m-3 6h3m14-6h3m-3 6h3"/>',
  download: '<path d="M12 3v12m-4-4 4 4 4-4M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
  upload: '<path d="M12 16V4m-4 4 4-4 4 4M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
  "chevron-right": '<path d="m9 18 6-6-6-6"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  moon: '<path d="M20.8 14.1A9 9 0 0 1 9.9 3.2a9 9 0 1 0 10.9 10.9Z"/>',
  monitor: '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8m-4-4v4"/>',
  sparkles: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3Zm7 11v6m-3-3h6M4 3v4M2 5h4"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  sliders: '<path d="M4 6h5m4 0h7M4 12h10m4 0h2M4 18h2m4 0h10"/><circle cx="11" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="8" cy="18" r="2"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Zm0 0v6h6M8 13h8m-8 4h5"/>',
  clipboard: '<rect x="5" y="5" width="14" height="16" rx="2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6m-6 4h6"/>',
  wrench: '<path d="m15 6 3-3a5 5 0 0 1-6 7L5 17a2 2 0 0 0 3 3l7-7a5 5 0 0 0 7-6l-3 3z"/>',
  chart: '<path d="M4 3v17h17M9 15v-4m5 4V8m5 7V5"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2m14-6a4 4 0 0 1 3 4v2M17 3a4 4 0 0 1 0 8"/><circle cx="10" cy="7" r="4"/>',
  flask: '<path d="M9 3h6m-5 0v7l-5 8a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-8V3M8 15h8"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  send: '<path d="m22 2-7 20-4-9-9-4zm0 0L11 13"/>',
  terminal: '<path d="m5 7 5 5-5 5m8 0h6"/><rect x="2" y="3" width="20" height="18" rx="2"/>',
};

const icon = (name) => `<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${icons[name] || icons.file}</svg>`;
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);
const $ = (id) => document.getElementById(id);
const section = (symbol, title, caption = "", color = "") =>
  `<div class="section-head"><span class="section-icon ${color}">${icon(symbol)}</span><div><h2>${esc(title)}</h2>${caption ? `<p>${esc(caption)}</p>` : ""}</div></div>`;
const badge = (label, color = "") => `<span class="badge ${color}">${esc(label)}</span>`;
const jsonBlock = (value) => `<pre>${esc(JSON.stringify(value, null, 2))}</pre>`;
const navItems = [
  ["build", "wand", "Agent factory"], ["dashboard", "chart", "Dashboard"], ["history", "history", "Run history"],
  ["chat", "message", "Agent chat"], ["tools", "box", "Tool registry"],
];
const stages = [
  ["intake", "clipboard", "Intake"], ["definition", "layers", "Define"], ["evals", "target", "Evaluate"],
  ["repair", "wrench", "Refine"], ["report", "chart", "Report"],
];
const state = {
  workspace: { demos: [], tools: {}, max_files: 30, max_file_bytes: 10485760 },
  runs: [], brief: "", files: [], demo: "", iterations: 3, model: true, checkpoint: false,
  tournament: true, token_budget: 12000, latency_budget: 120, regression: "", pending: false, active: null, tab: "overview", chatId: "", chats: {}, chatPending: {},
  session: null, blind: false, unseen_corpus: false, security_audit: false, minimum_confidence: "0", chatLanguage: "auto",
  reviewAnswers: {}, reviewEdits: {}, location: "build", runScreen: "", poll: null,
};
const titleFor = (kind) => ({
  answerable: "Answerable", cross_document: "Cross-document", out_of_scope: "Out of scope",
  ambiguous: "Ambiguous", elliptical: "Elliptical", answered: "Answered", refused: "Refused",
  clarify: "Clarification", error: "Error", queued: "Queued", running: "Running", complete: "Complete",
  approval: "Awaiting review", failed: "Failed",
})[kind] || kind;

async function api(path, options) {
  const response = await fetch(path, options);
  const payload = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(payload.detail) ? payload.detail.map((item) => item.msg).join(". ") : payload.detail;
    if (response.status === 401 && path !== "/api/session" && state.session?.required) clearSession();
    throw new Error(detail || "The workspace could not complete this request.");
  }
  return payload;
}

let toastTimer;
function toast(message) {
  const node = $("toast");
  node.textContent = message;
  node.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { node.hidden = true; }, 4000);
}

const isAdmin = () => state.session?.role === "admin";
const isStaff = () => isAdmin() || state.session?.role === "reviewer";
const visibleNav = () => navItems.filter(([key]) =>
  (key === "build" ? isAdmin() : ["dashboard", "history"].includes(key) ? isStaff() : state.session?.authenticated));

function refreshNav() {
  const active = state.location === "run" ? "history" : state.location;
  const nav = $("nav");
  const navState = active + ":" + state.session?.role;
  if (nav.dataset.current !== navState) {
    nav.dataset.current = navState;
    nav.innerHTML = visibleNav().map(([key, symbol, title]) => `
      <a href="#${key}" class="nav-item ${key === active ? "active" : ""}" ${key === active ? 'aria-current="page"' : ""}>${icon(symbol)} <span>${title}</span></a>`).join("");
  }
  $("page-name").textContent = state.location === "run" ? "Run report" : navItems.find(([key]) => key === active)?.[2] || "Sign in";
  $("sign-out").hidden = !state.session?.required || !state.session.authenticated;
  $("runtime-title").textContent = state.workspace.model_online ? "Local model online" : "Offline runtime";
  $("runtime-subtitle").textContent = state.workspace.model_online ? state.workspace.model : "Deterministic fallback";
  $("runtime-dot").classList.toggle("online", !!state.workspace.model_online);
}

function pipeline(run) {
  const key = run?.stage === "scoring" ? "evals" : run?.stage;
  const active = Math.max(0, stages.findIndex(([stage]) => stage === key));
  return `<div class="pipeline" aria-label="Build stages">${stages.map(([, symbol, title], i) =>
    `<div class="pipeline-step ${i < active || run?.status === "complete" ? "done" : i === active ? "active" : ""}" ${i === active && run?.status !== "complete" ? 'aria-current="step"' : ""}>
      <span>${icon(i < active || run?.status === "complete" ? "check" : symbol)}</span><span>${title}</span></div>`).join("")}</div>`;
}

function fileChips() {
  const example = state.workspace.demos.find((item) => item.id === state.demo);
  const file = (name, button = "") => `<span class="file-chip"><span>${icon("file")}</span><span title="${esc(name)}">${esc(name)}</span>${button}</span>`;
  const bundled = (example?.files || []).map((name) => file(name));
  const uploads = state.files.map((upload, i) => file(upload.name,
    `<button type="button" data-action="remove-file" data-value="${i}" aria-label="Remove ${esc(upload.name)}">${icon("close")}</button>`));
  return bundled.concat(uploads).join("") + (example ? `<button class="btn ghost small" type="button" data-action="clear-demo">Remove demo sources</button>` : "");
}

function demoCards() {
  return state.workspace.demos.map((item, index) => `
    <div class="demo ${state.demo === item.id ? "selected" : ""}">
      <span class="section-icon ${index ? "blue" : "teal"}">${icon(item.icon)}</span>
      <div><strong>${esc(item.name)}</strong><small>${esc(item.kind)}</small></div>
      <button type="button" class="btn ghost small" data-action="demo" data-value="${esc(item.id)}" aria-label="Load ${esc(item.name)}">${state.demo === item.id ? "Loaded" : "Load"}</button>
    </div>`).join("");
}

function buildScreen() {
  return `<div class="screen">
    <section class="hero">
      <div class="hero-copy">
        <h1>Build a <span>grounded agent.</span></h1>
        <p>Turn a brief and a document set into a tested agent with verifiable answers.</p>
      </div>
    </section>
    ${pipeline(state.active)}
    ${state.active && ["queued", "running", "approval"].includes(state.active.status) ? `
      <div class="info" style="margin-bottom:16px"><span class="spinner" aria-hidden="true"></span>
      ${esc(state.active.detail)} <a class="btn ghost small" href="#run/${esc(state.active.id)}">Open current run</a></div>` : ""}
    <div class="workspace-grid">
      <form id="build-form" class="card build-card">
        ${section("clipboard", "Define your agent", "Describe what the agent should do and supply its reference files.")}
        <div class="field">
          <label for="brief">Agent brief <span class="required">*</span></label>
          <textarea required id="brief" maxlength="4000" rows="4" placeholder="I need an assistant that answers questions about…">${esc(state.brief)}</textarea>
          <div class="field-meta"><span>Include the audience, scope, tone, and topics to refuse.</span><span id="brief-count">${state.brief.length.toLocaleString()} / 4,000</span></div>
        </div>
        <div class="field">
          <label for="files">Source documents <span class="required">*</span></label>
          <input type="file" id="files" accept=".pdf,.csv,.md,.txt,.docx${state.workspace.ocr_enabled ? ",.png,.jpg,.jpeg" : ""}" multiple hidden>
          <button class="drop-zone" id="drop-zone" data-action="browse" type="button" style="width:100%">
            <span class="section-icon">${icon("upload")}</span><span><strong>Drop files here or <span class="browse">browse files</span></strong>
            <p>PDF, CSV, Markdown, TXT, DOCX${state.workspace.ocr_enabled ? ", PNG, JPEG" : ""} · Up to 10 MB each</p></span>
          </button>
          <div id="file-list" class="file-list">${fileChips()}</div>
        </div>
        <div class="info bad" id="form-error" role="alert" hidden></div>
        <div class="actions build-actions">
          <button class="btn ghost" type="button" data-action="demo" data-value="people-ops">${icon("flask")} Try a demo</button>
          <button class="btn primary" type="submit" ${state.pending ? "disabled" : ""}>${state.pending ? '<span class="spinner"></span> Starting' : `${icon("sparkles")} Build agent`}</button>
        </div>
      </form>
      <aside class="rail" aria-label="Build configuration">
        <div class="card rail-card">
          ${section("sliders", "Build settings")}
          <div class="settings">
            <label for="iterations">Repair iterations</label>
            <select id="iterations">${[0, 1, 2, 3].map((count) => `<option value="${count}" ${state.iterations === count ? "selected" : ""}>${count === 0 ? "Baseline only" : `Up to ${count} ${count === 1 ? "iteration" : "iterations"}`}</option>`).join("")}</select>
            <label class="switch-row"><input id="model" type="checkbox" ${state.model ? "checked" : ""}><span>Use local model<small>Assist with drafting and evaluation.</small></span></label>
            <label class="switch-row"><input id="checkpoint" type="checkbox" ${state.checkpoint ? "checked" : ""}><span>Review requirements<small>Pause for your input before generation.</small></span></label>
            <label class="switch-row"><input id="tournament" type="checkbox" ${state.tournament ? "checked" : ""}><span>Prompt tournament<small>Compare three prompts on the same evaluation suite.</small></span></label>
            <details class="settings-details evidence-settings" ${state.blind || state.security_audit || Number(state.minimum_confidence) ? "open" : ""}>
              <summary>Evaluation and evidence</summary>
              <label class="switch-row"><input id="blind" type="checkbox" ${state.blind ? "checked" : ""}><span>Blind evaluation<small>Score held-out questions after optimization.</small></span></label>
              ${state.demo ? "" : `<label class="switch-row"><input id="unseen_corpus" type="checkbox" ${state.unseen_corpus ? "checked" : ""}><span>New corpus<small>Mark these uploads as a collection you have held back.</small></span></label>`}
              <label class="switch-row"><input id="security_audit" type="checkbox" ${state.security_audit ? "checked" : ""}><span>Security conformance<small>Check source and tool boundaries.</small></span></label>
              <label for="minimum_confidence">Minimum evidence score</label>
              <input id="minimum_confidence" form="build-form" type="number" required min="0" max="1" step=".01" value="${esc(state.minimum_confidence)}">
              <p class="muted">The agent declines to answer below this heuristic threshold. Zero disables the threshold.</p>
            </details>
            <details class="settings-details">
              <summary>Build budgets</summary>
              <div class="budget-fields">
                <div><label for="token_budget">Model tokens</label>
                  <input id="token_budget" form="build-form" type="number" required min="0" max="60000" step="1" value="${esc(state.token_budget)}"></div>
                <div><label for="latency_budget">Active seconds</label>
                  <input id="latency_budget" form="build-form" type="number" required min="1" max="600" step="1" value="${esc(state.latency_budget)}"></div>
              </div>
              <p class="muted">Review time is excluded. A repair with no score gain ends the loop.</p>
            </details>
            ${state.regression ? `<div class="info">Regression suite selected. <button type="button" class="btn ghost small" data-action="clear-regression">Remove</button></div>` : ""}
          </div>
        </div>
        <div class="card rail-card">${section("flask", "Sample projects", "Load a brief and its sample sources.")}
          <div class="demo-list">${demoCards()}</div>
          <div class="actions" style="margin-top:7px">
            <a href="#history" class="btn ghost small">View completed demos</a>
            <a href="/sample-documents" class="btn ghost small">${icon("download")} Sample files</a>
          </div>
        </div>
      </aside>
    </div>
  </div>`;
}

function historyScreen() {
  const rows = state.runs.map((item) => `<div class="history-row">
    <div><strong>${esc(item.name)}</strong><small>${item.demo ? "Recorded demonstration" : esc(new Date(item.created).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }))}</small></div>
    <div class="history-meta">
      ${badge(titleFor(item.status), item.status === "complete" ? "good" : item.status === "failed" ? "bad" : "warn")}
      ${item.score === undefined ? "" : badge(`${item.score}%`)}
    </div>
    <a class="btn small" href="#run/${esc(item.id)}">${icon("file")} Open run</a>
  </div>`).join("");
  return `<div class="screen"><div class="page-heading"><div><h1>Run history</h1><p>Open a recorded build, inspect its evidence, or test its agent.</p></div>
    ${isAdmin() ? `<a class="btn primary" href="#build">${icon("sparkles")} New build</a>` : ""}</div>
    <section class="card sheet">${section("history", "Builds")}${rows || `<div class="empty"><p>Build an agent to see its run here.</p></div>`}</section></div>`;
}

function toolsScreen() {
  const toolIcons = { csv_lookup: "clipboard", calculator: "terminal", current_date: "history", weather: "chart" };
  return `<div class="screen"><div class="page-heading"><div><h1>Tool registry</h1><p>The factory attaches only tools supported by the brief and its sources.</p></div></div>
    <div class="tools-grid">${Object.entries(state.workspace.tools).map(([key, tool]) =>
      `<article class="card tool-card">${section(toolIcons[key], tool.name, tool.description)}<code>${esc(tool.example)}</code></article>`).join("")}</div></div>`;
}

function scoreRows(cards) {
  return cards.map((item) => `<div class="score-row">
    <strong>${item.iteration ? `Iteration ${item.iteration}` : "Baseline"}</strong>
    <div class="score-track" role="progressbar" aria-label="Evaluation score" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${item.score}">
      <div class="score-fill" style="width:${item.score}%"></div></div>
    <strong>${item.score}%</strong></div>`).join("");
}

function checkRow(row) {
  const missing = row.missing_facts.map((item) => `<li>${esc(item.document)} · ${esc(item.fact)}</li>`).join("");
  const evidence = row.response.citations.map((item) => `<li>${esc(item.document)} · ${esc(item.heading)} · ${esc(item.locator)}</li>`).join("");
  return `<details class="result-row"><summary>${badge(row.id)}<span>${esc(row.question)}</span>
    ${badge(row.passed ? "Passed" : row.failure || "Failed", row.passed ? "good" : "bad")}</summary>
    <div class="result-body"><p>${badge(titleFor(row.category))} Expected ${esc(titleFor(row.expected_status))} · Received ${esc(titleFor(row.response.status))}</p>
    <p>Grounded ${row.checks.grounded ? "✓" : "✗"} · Correct ${row.checks.correct ? "✓" : "✗"}${row.checks.refused_when_expected === null ? "" : ` · Refused ${row.checks.refused_when_expected ? "✓" : "✗"}`}</p>
    <p><strong>Agent response</strong></p><p>${esc(row.response.answer)}</p>
    ${evidence ? `<ul class="list">${evidence}</ul>` : ""}
    ${missing ? `<p><strong>Missing evidence</strong></p><ul class="list">${missing}</ul>` : ""}</div></details>`;
}

function requirementsContent(req) {
  return `<p>${esc(req.scope)}</p>
    <ul class="list"><li><strong>Audience</strong> · ${esc(req.audience)}</li><li><strong>Tone</strong> · ${esc(req.tone)}</li></ul>
    <h3>Must answer</h3><ul class="list">${req.must_answer.map((item) => `<li>${esc(item.topic)} ${item.evidence.length ? `· <small>${esc(item.evidence.map((e) => e.document).join(", "))}</small>` : ""}</li>`).join("")}</ul>
    <h3>Must refuse</h3><ul class="list">${req.must_refuse.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
    <h3>Source documents</h3><ul class="list">${(req.documents || []).map((doc) => `<li>${esc(doc.name)}${doc.languages?.length ? ` · ${esc(doc.languages.join(", "))}` : ""}</li>`).join("")}</ul>
    ${req.groundability_gaps.map((item) => `<div class="info warn"><strong>${esc(item.topic)}</strong> · ${esc(item.reason)}</div>`).join("")}
    ${req.ingestion_warnings.map((text) => `<div class="info warn">${esc(text)}</div>`).join("")}`;
}

function reviewEditor(req) {
  const fields = [
    ["scope", "Scope", req.scope, 4], ["audience", "Audience", req.audience, 0], ["tone", "Tone", req.tone, 0],
    ["must_answer", "Topics to answer", req.must_answer.filter((item) => item.basis !== "document collection")
      .concat(req.groundability_gaps).map((item) => item.topic).join("\n"), 4],
    ["must_refuse", "Topics to refuse", req.must_refuse.slice(0, -1).join("\n"), 3],
  ];
  return `<details class="review-editor"><summary>Edit structured requirements</summary>
    <p class="muted">Use one topic per line. Edited topics are checked against the sources again before generation.</p>
    ${fields.map(([key, label, initial, rows]) => {
      const value = esc(state.reviewEdits[key] ?? initial);
      const input = rows ? `<textarea id="edit-${key}" maxlength="4000" rows="${rows}">${value}</textarea>`
        : `<input id="edit-${key}" type="text" maxlength="120" value="${value}">`;
      return `<div class="field"><label for="edit-${key}">${label}</label>${input}</div>`;
    }).join("")}</details>`;
}

function resultContent(run) {
  const result = run.result;
  const path = `/api/runs/${esc(run.id)}`;
  const download = (file, label) => `<a href="${path}/artifact/${file}" class="btn small">${icon("download")} ${label}</a>`;
  const invalidModel = result.model.calls.filter((call) => call.status !== "ok");
  if (state.tab === "engineering") return engineering.evidence(run);
  if (state.tab === "blind" && result.blind) {
    const blind = result.blind;
    const card = blind.scorecard;
    const origin = blind.corpus_origin === "user_supplied_unseen" ? "Requester-supplied new corpus" : "Held-out questions from the same corpus";
    return `<section class="card sheet">${section("target", "Blind evaluation", origin)}
      <div class="info"><strong>${card.passed} of ${card.total} passed · ${card.score}%</strong> · Scored after development decisions.</div>
      ${blind.results.map(checkRow).join("")}${download("blind_results.json", "Download blind results")}</section>`;
  }
  if (state.tab === "evaluations") {
    return `<section class="card sheet">${section("target", "Generated evaluation suite", "Expand a case to see its grounding, decision, and expected outcome.")}
      <div class="actions" style="margin-bottom:8px">${download("evals.json", "Evaluation cases")} ${download("eval_results.json", "All evaluations")}</div>
      ${result.results.map(checkRow).join("")}</section>`;
  }
  if (state.tab === "comparisons") {
    const tournament = result.tournament;
    const manual = result.manual_baseline;
    return `${tournament ? `<section class="card sheet">${section("target", "Prompt tournament",
      `Winner · ${tournament.winner}. Ties keep the earlier candidate.`)}
      ${tournament.candidates.map((entry) => `<details class="result-row"><summary><strong>${esc(entry.name)}</strong>
        ${badge(`${entry.scorecard.passed}/${entry.scorecard.total} · ${entry.scorecard.score}%`, entry.name === tournament.winner ? "good" : "")}</summary>
        <pre>${esc(entry.definition.system_prompt)}</pre></details>`).join("")}
      ${tournament.complete ? "" : '<div class="info warn">The active latency limit interrupted the tournament.</div>'}
      ${download("tournament.json", "Candidate evaluations")}</section>` : ""}
      ${manual ? `<section class="card sheet">${section("users", "Factory vs hand-written baseline",
        `Factory ${result.scorecard.passed}/${result.scorecard.total} · Hand-written ${manual.scorecard.passed}/${manual.scorecard.total}`)}
        <div class="info"><strong>Cases only the factory passed</strong> · ${esc(manual.changes.gained.join(", ") || "None")}</div>
        <div class="info"><strong>Cases only the hand-written agent passed</strong> · ${esc(manual.changes.lost.join(", ") || "None")}</div>
        <p class="muted">${manual.changes.unchanged.length} cases had the same outcome.</p>
        ${download("manual_comparison.json", "Baseline comparison")}</section>` : ""}`;
  }
  if (state.tab === "definition") {
    return `<section class="card sheet">${section("layers", "Agent definition", result.definition.description)}
      <div class="actions">${download("definition.json", "Definition JSON")}<button class="btn small" data-action="copy-definition">${icon("clipboard")} Copy JSON</button></div>
      ${jsonBlock(result.definition)}</section>`;
  }
  if (state.tab === "requirements") {
    return `<section class="card sheet">${section("clipboard", "Structured requirements")}${requirementsContent(result.requirements)}
      <div class="actions">${download("requirements.json", "Requirements JSON")}</div></section>`;
  }
  if (state.tab === "log") {
    return `<section class="card sheet">${section("wrench", "Targeted changes", result.stop_reason)}
      ${result.iterations.map((item) => `<div class="info"><strong>Iteration ${item.iteration} · ${esc(item.patch.replaceAll("_", " "))}</strong> ${badge(item.accepted ? "Accepted" : "Reverted", item.accepted ? "good" : "warn")}
        <p>${esc(item.why)} ${item.score_after === null ? `Scoring stopped at the latency limit after the ${item.score_before}% baseline.`
          : `${item.score_before}% to ${item.score_after}%.`}</p>
        <p>Addressed ${esc(item.addressed_cases.join(", ") || "none")} · Resolved ${esc(item.resolved_cases.join(", ") || "none")} · Regressed ${esc(item.regressed_cases.join(", ") || "none")}</p></div>`).join("") || '<p class="muted">No repairs were applied.</p>'}
      <div class="actions">${download("iterations.json", "Change log")} ${download("model_trace.json", "Model trace")}</div></section>
      <section class="card sheet">${section("cpu", "Model activity", `${result.model.name} · ${result.model.tokens} tokens · ${result.elapsed_seconds}s`)}
        ${result.model.calls.map((call) => `<div class="score-row"><strong>${esc(call.stage.replaceAll("_", " "))}</strong><span>${esc(call.status.replaceAll("_", " "))}</span><span>${call.tokens}</span></div>`).join("") || '<p class="muted">This run used the deterministic pipeline.</p>'}</section>`;
  }
  const failures = result.results.filter((item) => !item.passed);
  return `<section class="card sheet">${section("chart", "Score by iteration", result.stop_reason)}
      ${scoreRows(result.scorecards)}
      ${result.budget ? `<div class="info"><strong>Build budget</strong> · ${result.budget.active_seconds}/${result.budget.latency_limit} active seconds ·
        ${result.budget.tokens_used.toLocaleString()}/${result.budget.token_limit.toLocaleString()} model tokens</div>` : ""}
      ${(result.budget_notes || []).map((note) => `<div class="info warn">${esc(note)}</div>`).join("")}
    </section>
    <section class="card sheet">${section("target", "Remaining failures")}
      ${failures.length ? failures.map(checkRow).join("") : '<p class="muted">All cases in this generated suite passed. Performance on new questions can differ.</p>'}
      ${result.requirements.groundability_gaps.map((item) => `<div class="info warn"><strong>Source gap</strong> · ${esc(item.topic)}</div>`).join("")}
      ${invalidModel.length ? `<div class="info">${invalidModel.length} model calls used fallback or reached a limit. Open the run log for details.</div>` : ""}
      <div class="actions" style="margin-top:11px">${download("report.md", "Quality report")} ${download("scorecards.json", "Scorecards")}
      ${isAdmin() ? `<button class="btn small" data-action="regression">${icon("history")} Set as regression baseline</button>` : ""}</div>
    </section>
    ${result.regression ? `<section class="card sheet">${section("history", "Regression results", `${result.regression.scorecard.passed}/${result.regression.scorecard.total} cases from the prior run passed.`)}
      ${result.regression.prior_results_available ? `<div class="info">Newly failing · ${esc(result.regression.changes.lost.join(", ") || "None")}
        <br>Newly passing · ${esc(result.regression.changes.gained.join(", ") || "None")}</div>` : ""}
      ${result.regression.results.filter((row) => !row.passed).map(checkRow).join("")}${download("regression.json", "Regression results")}</section>` : ""}`;
}

function runScreen(run) {
  if (!run || run.id !== state.runScreen) {
    return `<div class="card empty"><span class="spinner"></span> Loading run</div>`;
  }
  if (run.status === "complete") {
    const result = run.result;
    const tabs = [["overview", "Overview"], ["evaluations", "Evaluations"], ["definition", "Definition"], ["requirements", "Requirements"], ["log", "Run log"]];
    if (result.blind) tabs.push(["blind", "Blind evaluation"]);
    tabs.push(["engineering", "Engineering lab"]);
    if (result.tournament || result.manual_baseline) tabs.splice(2, 0, ["comparisons", "Comparisons"]);
    return `<div class="screen"><div class="page-heading"><div><h1>${esc(run.name)}</h1><p>Factory report · ${run.demo ? "Recorded demonstration" : "Workspace build"}</p></div>
        <div class="actions"><a class="btn" href="#chat/${esc(run.id)}">${icon("message")} Open chat</a>
          <a class="btn primary" href="/api/runs/${esc(run.id)}/download">${icon("download")} Export run</a></div></div>
      <div class="panel-grid">
        <div class="card metric"><small>Final score</small><strong>${result.scorecard.score}%</strong><p>${result.scorecard.passed} of ${result.scorecard.total} cases passed</p></div>
        <div class="card metric"><small>Repair attempts</small><strong>${result.iterations.length}</strong><p>${result.iterations.filter((item) => item.accepted).length} accepted changes</p></div>
        <div class="card metric"><small>Attached tools</small><strong>${result.definition.tools.length}</strong><p>${esc(result.definition.tools.map((key) => state.workspace.tools[key]?.name || key).join(", ") || "Document retrieval only")}</p></div>
      </div>
      <div class="tabs" aria-label="Run report sections">${tabs.map(([key, label]) => `<button class="tab ${key === state.tab ? "active" : ""}" aria-pressed="${key === state.tab}" data-action="tab" data-value="${key}">${label}</button>`).join("")}</div>
      ${resultContent(run)}</div>`;
  }
  const review = run.review;
  return `<div class="screen"><div class="page-heading"><div><h1>${run.status === "approval" ? "Review requirements" : run.status === "failed" ? "Build interrupted" : "Building your agent"}</h1>
      <p aria-live="polite">${esc(run.detail)}</p></div>${badge(titleFor(run.status), run.status === "failed" ? "bad" : "warn")}</div>
    ${pipeline(run)}
    ${run.status === "approval" && review && !isAdmin() && !state.session.can_approve ?
      `<section class="card sheet">${section("clipboard", "Scope and source coverage")}${requirementsContent(review)}<p class="muted">Awaiting a reviewer with approval access.</p></section>` :
      run.status === "approval" && review ? `
      <form class="card sheet" id="review-form">${section("clipboard", "Scope and source coverage")}${requirementsContent(review)}${reviewEditor(review)}
      ${review.questions.map((q) => `<div class="field"><label for="review-${esc(q.id)}">${esc(q.text)}</label>
        <input type="text" id="review-${esc(q.id)}" name="${esc(q.id)}" maxlength="400" value="${esc(state.reviewAnswers[q.id] ?? "")}" placeholder="${esc(q.default || "Optional")}"></div>`).join("")}
      <button type="submit" class="btn primary">${icon("check")} Approve and continue</button></form>` :
      run.status === "failed" ? `<div class="card sheet"><a class="btn" href="#build">${icon("wand")} Return to factory</a></div>` :
      `<div class="card sheet"><strong><span class="spinner" aria-hidden="true"></span> ${esc(run.detail)}</strong>
      <div class="progress-track"><div class="progress-fill" style="width:${({intake: 12, definition: 30, evals: 51, scoring: 66, repair: 80, report: 96})[run.stage] || 8}%"></div></div></div>`}
    </div>`;
}

const feedbackCategories = [
  ["helpful", "Helpful answer"], ["incorrect_answer", "Incorrect answer"], ["missing_information", "Missing information"],
  ["wrong_citation", "Wrong citation"], ["incorrect_refusal", "Incorrect refusal"], ["inappropriate_response", "Inappropriate response"],
];

function chatResponse(item) {
  const response = item.response;
  if (!response) return `<div class="message user">${esc(item.question)}</div>`;
  const evidence = response.confidence;
  return `<div class="message">${badge(titleFor(response.status), response.status === "answered" ? "good" : response.status === "error" ? "bad" : "warn")}
    ${response.tool ? badge(state.workspace.tools[response.tool]?.name || response.tool) : ""}
    ${evidence ? badge(`Evidence ${Math.round(evidence.score * 100)}%`) : ""}
    <div>${esc(response.answer)}</div>
    ${response.citations.map((c) => `<details><summary>${esc(c.document)} · ${esc(c.heading)} · ${esc(c.locator)}</summary><p>${esc(c.quote)}</p>
      ${c.extraction ? `<p class="muted">OCR source · ${esc(c.extraction.confidence)} confidence</p>` : ""}</details>`).join("")}
    ${response.trace_id ? `<details class="chat-feedback"><summary>Give feedback</summary>
      <form data-feedback-trace="${esc(response.trace_id)}" data-run-id="${esc(state.chatId)}">
        <label class="field"><span class="field-label">Feedback type</span><select name="category">${feedbackCategories.map(([value, label]) => `<option value="${value}">${label}</option>`).join("")}</select></label>
        <label class="field"><span class="field-label">Comment</span><textarea name="comment" maxlength="1000" rows="2"></textarea></label>
        <button type="submit" class="btn small">Send feedback</button>
      </form></details>` : ""}</div>`;
}

function chatScreen() {
  const complete = state.runs.filter((item) => item.status === "complete");
  if (!complete.some((item) => item.id === state.chatId)) state.chatId = complete[0]?.id || "";
  const agent = complete.find((item) => item.id === state.chatId);
  const demo = state.workspace.demos.find((item) => item.id === state.chatId);
  const messages = state.chats[state.chatId] || [];
  return `<div class="screen"><div class="page-heading"><div><h1>Agent chat</h1><p>Ask a generated agent a question and inspect the supporting sources.</p></div></div>
    <div class="chat-grid">
      <aside class="card chat-list"><h3>Available agents</h3>${complete.map((item) => `<a class="btn small ${item.id === state.chatId ? "active" : ""}" href="#chat/${esc(item.id)}">${icon("message")} ${esc(item.name)}</a>`).join("") || '<p class="muted">Build an agent to start chatting.</p>'}</aside>
      <section class="card conversation">
        ${agent ? `<div class="chat-header">${section("message", agent.name)}
          <label class="field"><span class="field-label">Answer language</span><select id="chat-language">${[["auto", "Automatic"], ["en", "English"], ["hi", "Hindi"], ["ta", "Tamil"]].map(([key, label]) => `<option value="${key}" ${state.chatLanguage === key ? "selected" : ""}>${label}</option>`).join("")}</select></label></div>` : ""}
        <div class="thread" id="thread" aria-live="polite">
          ${messages.map(chatResponse).join("")}
          ${state.chatPending[state.chatId] ? '<div class="message"><span class="spinner"></span> Checking sources…</div>' : ""}
          ${agent && messages.length === 0 && demo ? `<div class="empty"><div class="section-icon">${icon("sparkles")}</div><button class="btn small" data-value="${esc(demo.example)}" data-action="chat-example">${esc(demo.example)}</button></div>` : ""}
        </div>
        <form class="chat-form" id="chat-form"><input type="text" name="question" id="chat-question" aria-label="Question" required maxlength="2000" placeholder="Ask about the supplied documents…" ${agent ? "" : "disabled"}>
          <button type="submit" class="btn primary" ${agent && !state.chatPending[state.chatId] ? "" : "disabled"}>${icon("send")} Send</button></form>
      </section>
    </div></div>`;
}

function loginScreen() {
  return `<section class="card login-panel">${section("layers", "Sign in to ForgeAI")}
    <form id="login-form">
      <div class="field"><label for="login-user">Username</label><input type="text" name="username" id="login-user" required maxlength="64" autocomplete="username"></div>
      <div class="field"><label for="login-password">Password</label><input type="password" name="password" id="login-password" required maxlength="256" autocomplete="current-password"></div>
      <p class="info bad" id="login-error" role="alert" hidden></p>
      <button class="btn primary" type="submit">Sign in</button>
    </form></section>`;
}

function clearSession() {
  cancelPoll();
  engineering.clear();
  Object.assign(state, {
    active: null, runs: [], files: [], brief: "", demo: "", regression: "", chats: {}, chatId: "", chatPending: {},
    reviewAnswers: {}, reviewEdits: {}, location: "login", runScreen: "", tab: "overview",
    session: {required: true, authenticated: false},
  });
  render();
}

async function openSession() {
  state.session = await api("/api/session");
  if (state.session.authenticated) state.workspace = await api("/api/workspace");
  route();
}

function render() {
  refreshNav();
  const screens = {
    build: buildScreen, dashboard: engineering.dashboard, history: historyScreen, tools: toolsScreen,
    chat: chatScreen, run: () => runScreen(state.active), login: loginScreen,
  };
  $("main").innerHTML = state.session ? screens[state.location]() : '<div class="card sheet" role="status">Connecting to workspace…</div>';
  const thread = $("thread");
  if (thread) thread.scrollTop = thread.scrollHeight;
}

async function loadRuns() {
  const session = state.session;
  const runs = await api("/api/runs");
  if (state.session === session) state.runs = runs;
}
function cancelPoll() {
  clearTimeout(state.poll);
  state.poll = null;
}

async function inspectRun(id, lookBusy = true) {
  cancelPoll();
  try {
    const run = await api(`/api/runs/${encodeURIComponent(id)}`);
    if (state.location !== "run" || state.runScreen !== id) return;
    const changed = !state.active || state.active.id !== id || state.active.status !== run.status || state.active.detail !== run.detail;
    state.active = run;
    if (changed || lookBusy) render();
    if (["queued", "running", "approval"].includes(run.status)) {
      state.poll = setTimeout(() => inspectRun(id, false), 700);
    } else {
      await loadRuns();
    }
  } catch (error) {
    if (state.location !== "run" || state.runScreen !== id) return;
    state.active = { id, status: "failed", detail: error.message };
    render();
  }
}

function route() {
  cancelPoll();
  const [view, id = ""] = window.location.hash.slice(1).split("/");
  const available = visibleNav().map(([key]) => key);
  const fallback = isAdmin() ? "build" : isStaff() ? "dashboard" : "chat";
  const permitted = available.includes(view) || (isStaff() && view === "run" && id);
  state.location = !state.session?.authenticated ? "login" : permitted ? view : fallback;
  if (state.location === "dashboard") engineering.loadDashboard();
  if (state.location === "run") {
    if (state.runScreen !== id) {
      state.tab = "overview";
      state.reviewAnswers = {};
      state.reviewEdits = {};
    }
    state.runScreen = id;
    inspectRun(id);
  } else if (state.location === "chat" && id) {
    state.chatId = id;
  }
  const menuWasOpen = $("sidebar").classList.contains("open");
  setMenu(false);
  render();
  if (menuWasOpen) $("main").focus();
  window.scrollTo(0, 0);
  if (state.location === "history" || state.location === "chat") {
    const location = state.location;
    loadRuns().then(() => {
      if (state.location === location) render();
    }).catch((error) => toast(error.message));
  }
}

function addFiles(files) {
  const supported = state.workspace.ocr_enabled ? /\.(pdf|csv|md|txt|docx|png|jpe?g)$/i : /\.(pdf|csv|md|txt|docx)$/i;
  const accepted = new Set(state.files.map((file) => file.name));
  const example = state.workspace.demos.find((item) => item.id === state.demo);
  const errors = [];
  for (const name of example?.files || []) accepted.add(name);
  for (const file of files) {
    if (!supported.test(file.name)) errors.push(`Unsupported file: ${file.name}`);
    else if (file.size > state.workspace.max_file_bytes) errors.push(`${file.name} exceeds 10 MB`);
    else if (accepted.has(file.name)) errors.push(`Duplicate filename: ${file.name}`);
    else if (accepted.size >= state.workspace.max_files) errors.push("The 30-file limit has been reached");
    else {
      accepted.add(file.name);
      state.files.push(file);
    }
  }
  $("file-list").innerHTML = fileChips();
  if (errors.length) toast(errors.join(". "));
}

async function build() {
  if (state.pending) return;
  const errorNode = $("form-error");
  if (!state.brief.trim() || (!state.files.length && !state.demo)) {
    errorNode.textContent = !state.brief.trim() ? "Enter an agent brief." : "Add at least one source document.";
    errorNode.hidden = false;
    return;
  }
  const form = new FormData();
  for (const key of ["brief", "iterations", "model", "checkpoint", "demo", "regression", "tournament", "token_budget", "latency_budget", "blind",
    "unseen_corpus", "security_audit", "minimum_confidence"]) form.append(key, state[key]);
  for (const file of state.files) form.append("files", file);
  const session = state.session;
  state.pending = true;
  render();
  try {
    const run = await api("/api/runs", { method: "POST", body: form });
    if (session !== state.session) return;
    state.active = run;
    window.location.hash = `#run/${run.id}`;
  } catch (error) {
    state.pending = false;
    render();
    if ($("form-error")) {
      $("form-error").textContent = error.message;
      $("form-error").hidden = false;
    } else toast(error.message);
  } finally {
    state.pending = false;
  }
}

async function sendMessage(question) {
  const runId = state.chatId;
  question = question.trim();
  if (!question || !runId || state.chatPending[runId]) return;
  state.chats[runId] ||= [];
  const messages = state.chats[runId];
  messages.push({ question });
  state.chatPending[runId] = true;
  render();
  try {
    const response = await api("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ run_id: runId, question, language: state.chatLanguage }),
    });
    messages.push({ response });
  } catch (error) {
    messages.push({ response: { status: "error", answer: error.message, citations: [] } });
  } finally {
    if (messages === state.chats[runId]) {
      state.chatPending[runId] = false;
      if (state.location === "chat" && state.chatId === runId) {
        render();
        $("chat-question").focus();
      }
    }
  }
}

const smallScreen = window.matchMedia?.("(max-width: 650px)");

function setMenu(open, restoreFocus = false) {
  const sidebar = $("sidebar");
  sidebar.classList.toggle("open", open);
  $("open-menu").setAttribute("aria-expanded", String(open));
  $("menu-backdrop").hidden = !open;
  document.querySelector(".main-shell").inert = open;
  $("skip-link").inert = open;
  document.body.classList.toggle("menu-open", open);
  if (open) {
    sidebar.setAttribute("role", "dialog");
    sidebar.setAttribute("aria-modal", "true");
    sidebar.setAttribute("aria-label", "Workspace navigation");
    $("close-menu").focus();
  } else {
    sidebar.removeAttribute("role");
    sidebar.removeAttribute("aria-modal");
    sidebar.removeAttribute("aria-label");
    if (restoreFocus) $("open-menu").focus();
  }
}

smallScreen?.addEventListener?.("change", (event) => { if (!event.matches) setMenu(false); });
$("skip-link").addEventListener("click", (event) => {
  event.preventDefault();
  $("main").focus();
});

document.querySelectorAll("[data-icon]").forEach((node) => { node.innerHTML = icon(node.dataset.icon); });
document.addEventListener("input", (event) => {
  const { id, value } = event.target;
  if (id === "brief") {
    state.brief = value;
    $("brief-count").textContent = `${value.length.toLocaleString()} / 4,000`;
  } else if (id.startsWith("review-")) state.reviewAnswers[event.target.name] = value;
  else if (id.startsWith("edit-")) state.reviewEdits[id.slice(5)] = value;
  else if (["token_budget", "latency_budget", "minimum_confidence"].includes(id)) state[id] = value;
});
document.addEventListener("change", (event) => {
  const { id, checked, value } = event.target;
  if (id === "files") {
    addFiles(event.target.files);
    event.target.value = "";
  } else if (id === "iterations") state.iterations = Number(value);
  else if (["model", "checkpoint", "tournament", "blind", "security_audit"].includes(id)) state[id] = checked;
  else if (id === "unseen_corpus") {
    state.unseen_corpus = checked;
    if (checked) state.blind = true;
    render();
  } else if (id === "chat-language") state.chatLanguage = value;
});
document.addEventListener("click", async (event) => {
  const navLink = event.target.closest('#sidebar a[href^="#"]');
  if (navLink && navLink.hash === window.location.hash && $("sidebar").classList.contains("open")) {
    setMenu(false);
    $("main").focus();
  }
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const { action, value } = button.dataset;
  if (action === "menu") setMenu(true);
  else if (action === "close-menu") setMenu(false, true);
  else if (action === "sign-out") {
    try {
      await api("/api/session", {method: "DELETE"});
      clearSession();
    } catch (error) {
      toast(error.message);
    }
  } else if (action === "browse") $("files").click();
  else if (action === "remove-file") {
    state.files.splice(Number(value), 1);
    $("file-list").innerHTML = fileChips();
  } else if (action === "clear-demo") {
    state.demo = "";
    render();
  } else if (action === "demo") {
    const item = state.workspace.demos.find((demo) => demo.id === value);
    if (!item) return;
    state.demo = item.id;
    state.unseen_corpus = false;
    if (item.regression) state.regression = item.regression;
    state.brief = item.brief;
    state.files = state.files.filter((file) => !item.files.includes(file.name));
    render();
    toast(`${item.name} loaded`);
  } else if (action === "tab") {
    state.tab = value;
    render();
    if (value === "engineering") engineering.open(state.runScreen);
    document.querySelector('.tab[aria-pressed="true"]')?.focus();
  } else if (action === "copy-definition") {
    try {
      await navigator.clipboard.writeText(JSON.stringify(state.active.result.definition, null, 2));
      toast("Definition copied");
    } catch {
      toast("Clipboard unavailable. Use the definition JSON download.");
    }
  } else if (action === "chat-example") sendMessage(value);
  else if (action === "regression") {
    state.regression = state.active.id;
    window.location.hash = "#build";
    toast("Regression baseline selected. Add the updated source collection.");
  } else if (action === "clear-regression") {
    state.regression = "";
    render();
  }
});
for (const eventName of ["dragover", "dragleave", "drop"]) {
  document.addEventListener(eventName, (event) => {
    const zone = event.target.closest("#drop-zone");
    if (!zone) return;
    event.preventDefault();
    zone.classList.toggle("dragging", eventName === "dragover");
    if (eventName === "drop") addFiles(event.dataTransfer.files);
  });
}
document.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (event.target.id === "login-form") {
    const form = event.target;
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      const values = new FormData(form);
      await api("/api/session", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(Object.fromEntries(values))});
      await openSession();
    } catch (error) {
      const message = $("login-error");
      if (message) {
        message.textContent = error.message;
        message.hidden = false;
      } else toast(error.message);
      button.disabled = false;
    }
  }
  if (event.target.id === "build-form") build();
  if (event.target.id === "chat-form") sendMessage($("chat-question").value);
  if (event.target.id === "review-form") {
    const button = event.target.querySelector("button[type=submit]");
    button.disabled = true;
    const id = state.runScreen;
    try {
      await api(`/api/runs/${encodeURIComponent(id)}/approve`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ answers: state.reviewAnswers, edits: state.reviewEdits }),
      });
      state.reviewAnswers = {};
      state.reviewEdits = {};
      inspectRun(id);
    } catch (error) {
      button.disabled = false;
      toast(error.message);
    }
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && $("sidebar").classList.contains("open")) setMenu(false, true);
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && state.location === "build") {
    event.preventDefault();
    $("build-form").requestSubmit();
  }
});
window.addEventListener("hashchange", route);
render();
openSession().catch((error) => {
  $("main").innerHTML = `<div class="card sheet info bad" role="alert">${esc(error.message)}</div>`;
});
