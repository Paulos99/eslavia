import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const PORT = 9343;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitFor(url) {
  for (let i = 0; i < 40; i++) {
    try {
      const res = await fetch(url);
      if (res.ok) return await res.json();
    } catch {}
    await sleep(250);
  }
  throw new Error("timeout");
}

const proc = spawn(
  EDGE,
  [
    "--headless=new",
    "--disable-gpu",
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${join(tmpdir(), `edge-qa-footer-${Date.now()}`)}`,
    "about:blank",
  ],
  { stdio: "ignore" },
);

try {
  await mkdir("tmp-qa", { recursive: true });
  const tabs = await waitFor(`http://127.0.0.1:${PORT}/json/list`);
  const page = tabs.find((t) => t.type === "page") || tabs[0];
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve);
    ws.addEventListener("error", reject);
  });
  let id = 0;
  const pending = new Map();
  ws.addEventListener("message", (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(JSON.stringify(msg.error)));
      else resolve(msg.result);
    }
  });
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const n = ++id;
      pending.set(n, { resolve, reject });
      ws.send(JSON.stringify({ id: n, method, params }));
    });

  async function shot(name) {
    const { data } = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    await writeFile(join("tmp-qa", name), Buffer.from(data, "base64"));
    console.log("wrote", name);
  }

  async function openAt(width, height, url = "http://localhost:5173/") {
    await send("Emulation.setDeviceMetricsOverride", {
      width,
      height,
      deviceScaleFactor: 1,
      mobile: width < 800,
    });
    await send("Page.navigate", { url });
    for (let i = 0; i < 40; i++) {
      const ready = await send("Runtime.evaluate", {
        expression: "!!document.querySelector('.footer')",
        returnByValue: true,
      });
      if (ready.result?.value) break;
      await sleep(200);
    }
    await send("Runtime.evaluate", {
      expression: `window.scrollTo(0, document.body.scrollHeight)`,
    });
    await sleep(500);
  }

  await send("Page.enable");
  await send("Runtime.enable");

  await openAt(1280, 900);
  const styles = await send("Runtime.evaluate", {
    expression: `(() => {
      const f = document.querySelector('.footer');
      const h = document.querySelector('.footer-heading');
      const a = document.querySelector('.footer-col a');
      const logo = document.querySelector('.footer .logo img');
      const cs = getComputedStyle(f);
      return {
        bg: cs.backgroundColor,
        color: cs.color,
        heading: h && getComputedStyle(h).color,
        link: a && getComputedStyle(a).color,
        filter: logo && getComputedStyle(logo).filter
      };
    })()`,
    returnByValue: true,
  });
  console.log("styles", JSON.stringify(styles.result?.value));
  await shot("footer-1280.png");

  await openAt(390, 900);
  await shot("footer-390.png");
} finally {
  proc.kill();
}
