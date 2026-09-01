import { sendWholesaleLead, discoverTelegramChatId } from "../server/telegram.mjs";

const token = String(process.env.TELEGRAM_BOT_TOKEN || "").trim();
if (!token) {
  console.error("Задайте TELEGRAM_BOT_TOKEN в .env");
  process.exit(1);
}

const chatId = await discoverTelegramChatId(token);
if (!chatId) {
  console.error("Чат не найден. Откройте @eslavia_opt_bot, нажмите Start и запустите скрипт снова.");
  process.exit(1);
}

console.log("TELEGRAM_CHAT_ID=" + chatId);
process.env.TELEGRAM_CHAT_ID = chatId;
const test = process.argv.includes("--test");
if (test) {
  const result = await sendWholesaleLead({
    name: "Тест с сайта",
    contact: "проверка бота",
    consent: true,
  });
  console.log(result);
}
