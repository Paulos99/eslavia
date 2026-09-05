import leadMail from "@data/lead-mail.json";

export function leadInbox(): string {
  return String(import.meta.env.VITE_LEAD_EMAIL || leadMail.to || "").trim();
}

export function formatLeadEmailFields({ name, contact }: { name: string; contact: string }) {
  const time = new Intl.DateTimeFormat("ru-RU", {
    timeZone: "Europe/Moscow",
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());

  return {
    _subject: "Эславия: заявка на оптовый прайс",
    _template: "table",
    _captcha: "false",
    Имя: name,
    Контакт: contact,
    Согласие: "получено",
    Источник: "сайт Эславия",
    Время: `${time} МСК`,
  };
}
