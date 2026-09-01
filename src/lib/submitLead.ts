import { formatWholesaleLeadMessage, leadActionKeyboard } from "./leadContact";

export async function submitLead(payload: {
  name: string;
  contact: string;
  consent: boolean;
}): Promise<{ ok: boolean; error?: string }> {
  const endpoint = import.meta.env.VITE_LEAD_API_URL || "/api/wholesale-lead";
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const text = await res.text();
    try {
      return JSON.parse(text) as { ok: boolean; error?: string };
    } catch {
      return sendLeadViaTelegram(payload);
    }
  } catch {
    return sendLeadViaTelegram(payload);
  }
}

async function sendLeadViaTelegram(payload: {
  name: string;
  contact: string;
}): Promise<{ ok: boolean; error?: string }> {
  const token = import.meta.env.VITE_TELEGRAM_BOT_TOKEN;
  const chatId = import.meta.env.VITE_TELEGRAM_CHAT_ID;
  if (!token || !chatId) {
    return { ok: false, error: "Не удалось отправить заявку" };
  }

  const body = new URLSearchParams({
    chat_id: chatId,
    text: formatWholesaleLeadMessage(payload),
    parse_mode: "HTML",
    disable_web_page_preview: "true",
  });
  const keyboard = leadActionKeyboard(payload.contact);
  if (keyboard) body.set("reply_markup", JSON.stringify(keyboard));

  try {
    await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: "POST",
      mode: "no-cors",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    return { ok: true };
  } catch {
    return { ok: false, error: "Не удалось отправить заявку" };
  }
}
