export const YANDEX_METRIKA_ID = 113120560;
export const CONSENT_KEY = "eslavia_cookie_consent";
export const OPEN_CONSENT_EVENT = "eslavia:open-cookie-consent";

export type Consent = "accepted" | "declined";

type YmFn = ((id: number, method: string, ...args: unknown[]) => void) & { a?: unknown[][]; l?: number };

declare global {
  interface Window {
    ym?: YmFn;
  }
}

const TAG_SRC = `https://mc.yandex.ru/metrika/tag.js?id=${YANDEX_METRIKA_ID}`;
let loaded = false;

export function getConsent(): Consent | null {
  try {
    const v = window.localStorage.getItem(CONSENT_KEY);
    return v === "accepted" || v === "declined" ? v : null;
  } catch {
    return null;
  }
}

export function setConsent(value: Consent) {
  try {
    window.localStorage.setItem(CONSENT_KEY, value);
  } catch {
    /* storage unavailable (private mode) — choice applies to this page view only */
  }
}

export function isMetrikaLoaded() {
  return loaded;
}

/** Official Yandex Metrika tag, executed only after the visitor has accepted cookies. */
export function loadMetrika() {
  if (loaded || typeof window === "undefined") return;
  loaded = true;
  /* eslint-disable */
  (function (m: any, e: Document, t: string, r: string, i: string) {
    m[i] =
      m[i] ||
      function () {
        (m[i].a = m[i].a || []).push(arguments);
      };
    m[i].l = 1 * (new Date() as any);
    for (let j = 0; j < e.scripts.length; j++) {
      if (e.scripts[j].src === r) return;
    }
    const k = e.createElement(t) as HTMLScriptElement;
    const a = e.getElementsByTagName(t)[0];
    k.async = true;
    k.src = r;
    if (a && a.parentNode) a.parentNode.insertBefore(k, a);
    else e.head.appendChild(k);
  })(window, document, "script", TAG_SRC, "ym");
  /* eslint-enable */
  window.ym!(YANDEX_METRIKA_ID, "init", {
    ssr: true,
    webvisor: true,
    clickmap: true,
    accurateTrackBounce: true,
    trackLinks: true,
  });
}

/** Removes Metrika's first-party cookies (_ym_*) and its localStorage keys after consent is withdrawn. */
export function clearMetrikaData() {
  const names = document.cookie
    .split(";")
    .map((c) => c.split("=")[0].trim())
    .filter((n) => n.startsWith("_ym"));
  const host = window.location.hostname;
  const domains = ["", host, `.${host}`, `.${host.replace(/^www\./, "")}`];
  for (const n of names) {
    for (const d of domains) {
      document.cookie = `${n}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/${d ? `; domain=${d}` : ""}`;
    }
  }
  try {
    for (let i = window.localStorage.length - 1; i >= 0; i--) {
      const key = window.localStorage.key(i);
      if (key && key.startsWith("_ym")) window.localStorage.removeItem(key);
    }
  } catch {
    /* ignore */
  }
}

export function openCookieConsent() {
  window.dispatchEvent(new Event(OPEN_CONSENT_EVENT));
}
