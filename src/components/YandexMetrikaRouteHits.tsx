import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

export const YANDEX_METRIKA_ID = 113120560;

declare global {
  interface Window {
    ym?: (id: number, method: string, ...args: unknown[]) => void;
  }
}

/**
 * Sends a Yandex Metrika hit on client-side route changes.
 * The initial pageview is recorded by the tag in index.html (ym init), so it is skipped here.
 */
export function YandexMetrikaRouteHits() {
  const location = useLocation();
  const prevUrl = useRef<string | null>(null);

  useEffect(() => {
    const url = location.pathname + location.search;
    if (prevUrl.current === null) {
      prevUrl.current = url;
      return;
    }
    if (prevUrl.current === url) return;
    const referer = window.location.origin + prevUrl.current;
    prevUrl.current = url;
    window.ym?.(YANDEX_METRIKA_ID, "hit", window.location.href, { referer });
  }, [location.pathname, location.search]);

  return null;
}
