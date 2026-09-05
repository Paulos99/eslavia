export function yandexFormIframeSrc(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  const fromHtml = trimmed.match(/src=["']([^"']+)["']/i);
  const url = (fromHtml?.[1] || trimmed).trim();
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    if (!host.endsWith("yandex.ru") && !host.endsWith("yandex.com") && host !== "ya.ru") {
      return "";
    }
    parsed.searchParams.set("iframe", "1");
    return parsed.toString();
  } catch {
    return "";
  }
}

export function yandexFormFrameName(src: string): string {
  const match = src.match(/\/(?:u|cloud)\/([a-zA-Z0-9]+)/);
  return match ? `ya-form-${match[1]}` : "ya-form";
}
