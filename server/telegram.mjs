import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function loadEnv() {
  const envPath = join(root, ".env");
  if (!existsSync(envPath)) return;
  for (const line of readFileSync(envPath, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const i = trimmed.indexOf("=");
    if (i < 1) continue;
    const key = trimmed.slice(0, i).trim();
    const val = trimmed.slice(i + 1).trim().replace(/^["']|["']$/g, "");
    if (!process.env[key]) process.env[key] = val;
  }
}

loadEnv();

export async function sendWholesaleLead(body) {
  const name = String(body?.name || "").trim();
  const contact = String(body?.contact || "").trim();
  const consent = Boolean(body?.consent);

  if (!name || !contact) {
    return { ok: false, error: "Укажите имя и контакт" };
  }
  if (!consent) {
    return { ok: false, error: "Нужно согласие на обработку персональных данных" };
  }

  if (process.env.LEAD_ADAPTER === "mock") {
    return { ok: true, mock: true };
  }

  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) {
    return {
      ok: false,
      error: "Заявка не отправлена: не настроен Telegram (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID).",
    };
  }

  const text = [
    "Новая заявка на оптовый прайс — Таисия",
    `Имя: ${name}`,
    `Контакт: ${contact}`,
    "Согласие на обработку ПДн: да",
  ].join("\n");

  try {
    const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, text }),
    });
    const data = await res.json();
    if (!data.ok) {
      return { ok: false, error: "Не удалось отправить заявку в Telegram." };
    }
    return { ok: true };
  } catch {
    return { ok: false, error: "Сеть недоступна, заявка не отправлена." };
  }
}
