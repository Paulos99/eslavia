import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function readJsonTo() {
  const file = join(root, "data", "lead-mail.json");
  if (!existsSync(file)) return "";
  try {
    const parsed = JSON.parse(readFileSync(file, "utf8"));
    return String(parsed?.to || "").trim();
  } catch {
    return "";
  }
}

export function getLeadEmail() {
  return String(
    process.env.MAIL_TO || process.env.LEAD_EMAIL || process.env.VITE_LEAD_EMAIL || readJsonTo() || "pavel199975@ya.ru",
  ).trim();
}

function formatLeadTime() {
  return new Intl.DateTimeFormat("ru-RU", {
    timeZone: "Europe/Moscow",
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
}

export async function sendLeadEmail({ name, contact }) {
  const to = getLeadEmail();
  if (!to) {
    return { ok: false, error: "Не указан адрес для заявок" };
  }

  const payload = {
    _subject: "Эславия: заявка на оптовый прайс",
    _template: "table",
    _captcha: "false",
    Имя: name,
    Контакт: contact,
    Согласие: "получено",
    Источник: "сайт Эславия",
    Время: `${formatLeadTime()} МСК`,
  };

  const origin = String(process.env.LEAD_FORM_ORIGIN || process.env.LEAD_CORS_ORIGIN || "https://paulos99.github.io").trim();

  try {
    const res = await fetch(`https://formsubmit.co/ajax/${encodeURIComponent(to)}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        Origin: origin,
        Referer: `${origin.replace(/\/$/, "")}/eslavia/`,
      },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    const success = data.success === true || data.success === "true";
    const activation = String(data.message || "").toLowerCase().includes("activation");
    if (activation) {
      console.warn("lead email: confirm FormSubmit activation in", to);
      return { ok: true, activation: true };
    }
    if (!res.ok || !success) {
      console.error("lead email failed", data);
      return { ok: false, error: "Не удалось отправить заявку на почту" };
    }
    return { ok: true };
  } catch (error) {
    console.error("lead email network failed", error);
    return { ok: false, error: "Сеть недоступна, заявка не отправлена." };
  }
}
