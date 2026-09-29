/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LEAD_API_URL?: string;
  readonly VITE_LEAD_EMAIL?: string;
}

declare module "*.md?raw" {
  const content: string;
  export default content;
}
