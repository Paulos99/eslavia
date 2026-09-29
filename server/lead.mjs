import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { sendLeadEmail } from "./mail.mjs";

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

function normalizePhone(raw) {
  let digits = String(raw).replace(/\D/g, "");
  if (digits.length === 11 && digits.startsWith("8")) digits = `7${digits.slice(1)}`;
  if (digits.length === 10 && digits.startsWith("9")) digits = `7${digits}`;
  if (digits.length < 11 || digits.length > 15) return "";
  return digits;
}

function isTrivialNumber(digits) {
  if (/^(\d)\1+$/.test(digits)) return true;
  if (new Set(digits).size < 4) return true;
  const tail = digits.slice(-10);
  if ("012345678901234567890".includes(tail) || "98765432109876543210".includes(tail)) return true;
  const last7 = digits.slice(-7);
  if (/^(\d)\1+$/.test(last7) || last7 === "1234567" || last7 === "7654321") return true;
  return false;
}

export function validateLeadContact(raw) {
  const value = String(raw || "").trim();
  if (!value) return { ok: false, error: "Укажите телефон, Telegram или e-mail" };
  if (/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value)) return { ok: true };
  if (
    /^@[A-Za-z][A-Za-z0-9_]{4,}$/.test(value) ||
    /^(?:https?:\/\/)?(?:www\.)?t\.me\/[A-Za-z][A-Za-z0-9_]{4,}/i.test(value)
  ) {
    return { ok: true };
  }
  const digits = value.replace(/\D/g, "");
  if (!digits) return { ok: false, error: "Введите телефон, Telegram или e-mail" };
  if (digits.length < 10 || !normalizePhone(value) || isTrivialNumber(digits)) {
    return { ok: false, error: "Введите настоящий номер телефона" };
  }
  return { ok: true };
}

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
  const contactCheck = validateLeadContact(contact);
  if (!contactCheck.ok) {
    return { ok: false, error: contactCheck.error };
  }

  if (process.env.LEAD_ADAPTER === "mock") {
    return { ok: true, mock: true };
  }

  return sendLeadEmail({ name, contact });
}
