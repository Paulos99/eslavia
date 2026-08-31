import { copyFileSync, existsSync } from "node:fs";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { sendWholesaleLead } from "./server/telegram.mjs";

const repoName = process.env.GITHUB_REPOSITORY?.split("/")[1];

export default defineConfig({
  base: repoName ? `/${repoName}/` : "/",
  plugins: [
    react(),
    {
      name: "wholesale-lead",
      configureServer(server) {
        server.middlewares.use(async (req, res, next) => {
          if (!req.url?.startsWith("/api/wholesale-lead")) {
            next();
            return;
          }
          if (req.method !== "POST") {
            res.statusCode = 405;
            res.end("Method Not Allowed");
            return;
          }
          const chunks = [];
          for await (const chunk of req) chunks.push(chunk);
          let body = {};
          try {
            body = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
          } catch {
            res.statusCode = 400;
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify({ ok: false, error: "Некорректный запрос" }));
            return;
          }
          const result = await sendWholesaleLead(body);
          res.statusCode = result.ok ? 200 : 502;
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(result));
        });
      },
    },
    {
      name: "spa-github-pages",
      closeBundle() {
        const index = path.resolve("dist/index.html");
        if (existsSync(index)) copyFileSync(index, path.resolve("dist/404.html"));
      },
    },
  ],
  resolve: {
    alias: {
      "@data": path.resolve(__dirname, "data"),
    },
  },
});
