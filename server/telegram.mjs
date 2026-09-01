import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const BOT_USERNAME = "eslavia_opt_bot";

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

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
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

export function formatWholesaleLeadMessage({ name, contact }) {
  return [
    "⭐ <b>Новая заявка с сайта</b>",
    "<i>Кто-то запросил оптовый прайс Эславии</i>",
    "",
    "<blockquote>",
    `<b>Имя</b>\n${escapeHtml(name)}`,
    "",
    `<b>Контакт</b>\n<code>${escapeHtml(contact)}</code>`,
    "</blockquote>",
    "",
    "✅ Согласие на обработку ПДн получено",
    `<i>${formatLeadTime()} МСК</i>`,
  ].join("\n");
}

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

function contactCard({ name, phone }) {
  const firstName = (name || "Заявка Эславия").slice(0, 64);
  return {
    phone_number: `+${phone}`,
    first_name: firstName,
    vcard: ["BEGIN:VCARD", "VERSION:3.0", `FN:${firstName}`, `TEL;TYPE=CELL:+${phone}`, "END:VCARD"].join("\n"),
  };
}

const pendingContactByPhone = new Map();

export function leadActionKeyboard(contact) {
  const phone = normalizePhone(contact);
  if (!phone) return undefined;
  return {
    inline_keyboard: [[{ text: "Добавить в контакты", callback_data: `add:${phone}` }]],
  };
}

async function telegram(token, method, payload) {
  const res = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

async function sendLeadContact(token, chatId, { name, phone }) {
  return telegram(token, "sendContact", {
    chat_id: chatId,
    ...contactCard({ name, phone }),
  });
}

let pollStarted = false;

export function startTelegramCallbackPoller() {
  const token = String(process.env.TELEGRAM_BOT_TOKEN || "").trim();
  if (pollStarted || !token) return;
  pollStarted = true;
  let offset = 0;
  (async () => {
    while (true) {
      try {
        const data = await telegram(token, "getUpdates", {
          offset,
          timeout: 25,
          allowed_updates: ["callback_query"],
        });
        if (!data.ok) {
          await new Promise((resolve) => setTimeout(resolve, 3000));
          continue;
        }
        for (const update of data.result || []) {
          offset = update.update_id + 1;
          const query = update.callback_query;
          if (!query?.data?.startsWith("add:")) continue;
          const phone = query.data.slice(4);
          const name = pendingContactByPhone.get(phone) || "Заявка Эславия";
          await telegram(token, "answerCallbackQuery", { callback_query_id: query.id });
          if (!phone) continue;
          const sent = await sendLeadContact(token, String(query.message?.chat?.id || ""), { name, phone });
          if (!sent.ok) console.error("telegram sendContact failed", sent);
        }
      } catch {
        await new Promise((resolve) => setTimeout(resolve, 3000));
      }
    }
  })();
}

let cachedChatId = "";

export async function discoverTelegramChatId(token) {
  const data = await telegram(token, "getUpdates", { limit: 100, timeout: 0 });
  if (!data.ok) {
    console.error("telegram getUpdates failed", data);
    return "";
  }

  const chats = [];
  for (const update of data.result || []) {
    const chat =
      update.message?.chat ||
      update.edited_message?.chat ||
      update.my_chat_member?.chat ||
      update.channel_post?.chat;
    if (chat?.id) chats.push(chat);
  }
  const privateChat = [...chats].reverse().find((chat) => chat.type === "private");
  const fallback = [...chats].reverse()[0];
  return String((privateChat || fallback)?.id || "");
}

export async function resolveTelegramChatId(token) {
  const configured = String(process.env.TELEGRAM_CHAT_ID || "").trim();
  if (configured) return configured;
  if (cachedChatId) return cachedChatId;
  cachedChatId = await discoverTelegramChatId(token);
  return cachedChatId;
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

  const token = String(process.env.TELEGRAM_BOT_TOKEN || "").trim();
  if (!token) {
    return {
      ok: false,
      error: "Заявка не отправлена: не настроен Telegram-бот.",
    };
  }

  let chatId;
  try {
    chatId = await resolveTelegramChatId(token);
  } catch {
    return { ok: false, error: "Сеть недоступна, заявка не отправлена." };
  }

  if (!chatId) {
    return {
      ok: false,
      error: `Напишите боту @${BOT_USERNAME} команду /start и отправьте заявку ещё раз.`,
    };
  }

  try {
    const payload = {
      chat_id: chatId,
      text: formatWholesaleLeadMessage({ name, contact }),
      parse_mode: "HTML",
      disable_web_page_preview: true,
    };
    const keyboard = leadActionKeyboard(contact);
    if (keyboard) payload.reply_markup = keyboard;
    const data = await telegram(token, "sendMessage", payload);
    if (!data.ok) {
      console.error("telegram sendMessage failed", data);
      return { ok: false, error: "Не удалось отправить заявку в Telegram." };
    }
    const phone = normalizePhone(contact);
    if (phone) pendingContactByPhone.set(phone, name);
    return { ok: true };
  } catch {
    return { ok: false, error: "Сеть недоступна, заявка не отправлена." };
  }
}
