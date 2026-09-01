import { createServer } from "node:http";
import { readFileSync, existsSync, statSync } from "node:fs";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";
import { sendWholesaleLead, startTelegramCallbackPoller } from "./telegram.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const dist = join(__dirname, "..", "dist");
const port = Number(process.env.PORT || 4173);
const corsOrigin = process.env.LEAD_CORS_ORIGIN || "https://paulos99.github.io";

function setCors(res) {
  res.setHeader("Access-Control-Allow-Origin", corsOrigin);
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

const types = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".webp": "image/webp",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".xml": "application/xml",
  ".txt": "text/plain; charset=utf-8",
  ".pdf": "application/pdf",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

function send(res, code, body, headers = {}) {
  res.writeHead(code, headers);
  res.end(body);
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url || "/", `http://${req.headers.host}`);

  if (url.pathname === "/api/wholesale-lead") {
    setCors(res);
    if (req.method === "OPTIONS") {
      send(res, 204, "");
      return;
    }
    if (req.method !== "POST") {
      send(res, 405, JSON.stringify({ ok: false, error: "Method Not Allowed" }), {
        "Content-Type": "application/json",
      });
      return;
    }
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    let body = {};
    try {
      body = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
    } catch {
      send(res, 400, JSON.stringify({ ok: false, error: "Некорректный запрос" }), {
        "Content-Type": "application/json",
      });
      return;
    }
    const result = await sendWholesaleLead(body);
    send(res, result.ok ? 200 : 502, JSON.stringify(result), {
      "Content-Type": "application/json",
    });
    return;
  }

  let filePath = join(dist, decodeURIComponent(url.pathname));
  if (!normalize(filePath).startsWith(normalize(dist))) {
    send(res, 403, "Forbidden");
    return;
  }
  if (url.pathname === "/" || !extname(filePath) || !existsSync(filePath)) {
    const spa = join(dist, "index.html");
    if (existsSync(spa)) {
      send(res, 200, readFileSync(spa), { "Content-Type": types[".html"] });
      return;
    }
    send(res, 404, "Not found");
    return;
  }
  if (!statSync(filePath).isFile()) {
    send(res, 404, "Not found");
    return;
  }
  send(res, 200, readFileSync(filePath), {
    "Content-Type": types[extname(filePath)] || "application/octet-stream",
  });
});

server.listen(port, () => {
  startTelegramCallbackPoller();
  console.log(`Eslavia server http://localhost:${port}`);
});
