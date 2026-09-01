export function normalizePhone(raw: string): string {
  let digits = String(raw).replace(/\D/g, "");
  if (digits.length === 11 && digits.startsWith("8")) digits = `7${digits.slice(1)}`;
  if (digits.length === 10 && digits.startsWith("9")) digits = `7${digits}`;
  if (digits.length < 11 || digits.length > 15) return "";
  return digits;
}

function isTrivialNumber(digits: string): boolean {
  if (/^(\d)\1+$/.test(digits)) return true;
  if (new Set(digits).size < 4) return true;
  const tail = digits.slice(-10);
  const seq = "012345678901234567890";
  const rev = "98765432109876543210";
  if (seq.includes(tail) || rev.includes(tail)) return true;
  const last7 = digits.slice(-7);
  if (/^(\d)\1+$/.test(last7) || last7 === "1234567" || last7 === "7654321") return true;
  return false;
}

export function validateLeadContact(raw: string): { ok: true } | { ok: false; error: string } {
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
  if (!digits) {
    return { ok: false, error: "Введите телефон, Telegram или e-mail" };
  }
  if (digits.length < 10 || !normalizePhone(value) || isTrivialNumber(digits)) {
    return { ok: false, error: "Введите настоящий номер телефона" };
  }
  return { ok: true };
}

function escapeHtml(value: string): string {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatLeadTime(): string {
  return new Intl.DateTimeFormat("ru-RU", {
    timeZone: "Europe/Moscow",
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
}

export function formatWholesaleLeadMessage({ name, contact }: { name: string; contact: string }): string {
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

export function leadActionKeyboard(contact: string): { inline_keyboard: { text: string; callback_data: string }[][] } | undefined {
  const phone = normalizePhone(contact);
  if (!phone) return undefined;
  return {
    inline_keyboard: [[{ text: "Добавить в контакты", callback_data: `add:${phone}` }]],
  };
}
