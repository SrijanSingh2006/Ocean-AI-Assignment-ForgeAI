import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";

const app = process.env.FORGE_SMOKE_URL || "http://127.0.0.1:8874";
const output = process.env.FORGE_SCREENSHOTS || ".runs/ui-qa";
const debugPort = process.env.FORGE_CHROMIUM_DEBUG_PORT || "9227";
const tabs = await (await fetch(`http://127.0.0.1:${debugPort}/json/list`)).json();
const socket = new WebSocket(tabs.find((tab) => tab.type === "page").webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

let nextId = 0;
const pending = new Map();
const pageErrors = [];
socket.addEventListener("message", ({ data }) => {
  const message = JSON.parse(data);
  if (message.method === "Runtime.exceptionThrown") pageErrors.push(message.params.exceptionDetails.exception?.description);
  if (!message.id) return;
  const handlers = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) handlers.reject(new Error(message.error.message));
  else handlers.resolve(message.result);
});

function send(method, params = {}) {
  const id = ++nextId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({method, params, id}));
  });
}

async function evaluate(expression) {
  const result = await send("Runtime.evaluate", {expression, awaitPromise: true, returnByValue: true});
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
  return result.result.value;
}

async function waitFor(expression) {
  const until = Date.now() + 15000;
  while (Date.now() < until) {
    try {
      if (await evaluate(expression)) return;
    } catch (error) {
      if (!error.message.includes("context")) throw error;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Timed out waiting for ${expression}\n${await evaluate("document.querySelector('main')?.innerText")}`);
}

const text = (needle) => `document.querySelector('main')?.innerText?.includes(${JSON.stringify(needle)})`;
const click = (selector) => evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
const follow = async (hash) => evaluate(`location.hash = ${JSON.stringify(hash)}`);
const fill = (selector, value) => evaluate(`(() => {
  const input = document.querySelector(${JSON.stringify(selector)});
  input.value = ${JSON.stringify(value)};
  input.dispatchEvent(new Event("change", {bubbles: true}));
})()`);
const submit = (selector) => evaluate(`document.querySelector(${JSON.stringify(selector)}).requestSubmit()`);
const viewport = (width, height, mobile = false) =>
  send("Emulation.setDeviceMetricsOverride", {width, height, deviceScaleFactor: 1, mobile});
const screenshot = async (name) => {
  await evaluate("Promise.race([Promise.allSettled(document.getAnimations().filter(animation => Number.isFinite(animation.effect.getComputedTiming().endTime)).map(animation => animation.finished)), new Promise(resolve => setTimeout(resolve, 600))])");
  const {data} = await send("Page.captureScreenshot", {format: "jpeg", quality: 87, fromSurface: true});
  await writeFile(`${output}/${name}.jpg`, Buffer.from(data, "base64"));
};

try {
  await mkdir(output, {recursive: true});
  await send("Runtime.enable");
  await send("Page.enable");
  await viewport(1400, 1000);
  await send("Page.navigate", {url: app});
  await waitFor(text("grounded agent."));
  await click("[data-theme-choice=system]");
  await send("Emulation.setEmulatedMedia", {features: [{name: "prefers-color-scheme", value: "light"}]});
  await waitFor("document.documentElement.dataset.theme === 'light'");
  await screenshot("factory-light");
  await click("[data-theme-toggle]");
  assert.equal(await evaluate("document.documentElement.dataset.theme"), "dark");
  await send("Page.reload");
  await waitFor(text("grounded agent."));
  assert.equal(await evaluate("document.documentElement.dataset.theme"), "dark");
  await screenshot("factory-dark");
  await click("[data-theme-choice=system]");
  await send("Emulation.setEmulatedMedia", {features: [{name: "prefers-color-scheme", value: "light"}]});
  await waitFor("document.documentElement.dataset.theme === 'light'");
  await follow("#build");

  await click('[data-action=demo][data-value=people-ops]');
  await click(".evidence-settings summary");
  await click("#blind");
  await click("#security_audit");
  await click("#model");
  await submit("#build-form");
  await waitFor(text("Engineering lab"));
  const run = await evaluate("location.hash.split('/')[1]");
  assert.match(run, /^[a-f0-9]{12}$/);

  await click('[data-action=tab][data-value=blind]');
  await waitFor(text("8 passed"));
  assert.equal(await evaluate("document.querySelectorAll('.result-row').length"), 8);
  await screenshot("blind-results");
  await click('[data-action=tab][data-value=engineering]');
  await waitFor(text("No comparable policy disagreements"));
  await click('[data-lab-panel=security]');
  await waitFor(text("Run conformance checks"));
  await submit("[data-engineering-form=security]");
  await waitFor("document.querySelector('.lab-content .badge.good') !== null");
  await click('[data-lab-panel=languages]');
  await waitFor(text("Evaluate supported languages"));
  await submit("[data-engineering-form=languages]");
  await waitFor(text("unavailable"));
  await click("[data-lab-panel=releases]");
  await waitFor(text("Export runnable agent"));
  const href = await evaluate("document.querySelector('.lab-content a').href");
  const payload = await fetch(href);
  assert.equal(payload.status, 200);
  const bytes = Buffer.from(await payload.arrayBuffer());
  assert.equal(bytes.subarray(0, 2).toString(), "PK");
  await writeFile(`${output}/browser-export.zip`, bytes);
  await submit("[data-engineering-form=release]");
  await waitFor("document.querySelector('[data-release-op=approve]') !== null");
  await click("[data-release-op=approve]");
  await waitFor("document.querySelector('[data-release-op=activate]') !== null");
  await click("[data-release-op=activate]");
  await waitFor(text("· Active"));

  await follow(`#chat/${run}`);
  await waitFor("document.querySelector('#chat-question') && !document.querySelector('#chat-question').disabled");
  await fill("#chat-language", "en");
  await fill("#chat-question", "How many annual leave days does a full-time employee receive?");
  await submit("#chat-form");
  await waitFor("document.querySelector('.message:not(.user) [data-feedback-trace]') !== null");
  await waitFor(text("22"));
  await waitFor(text("Evidence"));
  await screenshot("chat-evidence");
  await click(".chat-feedback summary");
  await fill("[data-feedback-trace] textarea", "The leave allowance citation is useful.");
  await submit("[data-feedback-trace]");
  await waitFor("document.querySelector('[data-feedback-trace]').hidden");

  await follow(`#run/${run}`);
  await waitFor(text("Engineering lab"));
  await click('[data-action=tab][data-value=engineering]');
  await click('[data-lab-panel=feedback]');
  await waitFor(text("The leave allowance citation is useful."));
  await click('[data-lab-panel=traces]');
  await waitFor(text("Open timeline"));
  await click("[data-trace]");
  await waitFor(text("normalized"));
  await screenshot("execution-trace");
  await follow("#dashboard");
  await waitFor(text("Generated agents"));
  await waitFor(`document.querySelector('main a[href="#run/${run}"]') !== null`);
  await waitFor("document.querySelector('#toast').hidden");
  await screenshot("dashboard");
  await viewport(393, 852, true);
  await waitFor("matchMedia('(max-width: 650px)').matches");
  await send("Input.dispatchKeyEvent", {type: "rawKeyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9});
  await send("Input.dispatchKeyEvent", {type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9});
  assert.ok(await evaluate("document.activeElement && document.activeElement !== document.body"));
  await click("#open-menu");
  assert.equal(await evaluate("document.querySelector('#sidebar').getAttribute('role')"), "dialog");
  await send("Input.dispatchKeyEvent", {type: "rawKeyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27});
  await waitFor("!document.querySelector('#sidebar').classList.contains('open')");
  await send("Emulation.setEmulatedMedia", {features: [{name: "prefers-reduced-motion", value: "reduce"}]});
  assert.ok(await evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"));
  await screenshot("dashboard-mobile");
  assert.deepEqual(pageErrors, []);
  console.log(`Chromium passed factory, themes, blind evaluation, conformance, languages, release approval/activation, export, sourced chat, feedback, traces, dashboard, mobile, keyboard and reduced motion. Run ${run}`);
} finally {
  socket.close();
}
