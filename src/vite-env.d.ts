/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LEAD_API_URL?: string;
  readonly VITE_LEAD_EMAIL?: string;
  readonly VITE_TELEGRAM_BOT_TOKEN?: string;
  readonly VITE_TELEGRAM_CHAT_ID?: string;
}

declare module "*.md?raw" {
  const content: string;
  export default content;
}
