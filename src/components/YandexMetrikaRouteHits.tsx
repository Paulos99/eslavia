import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { YANDEX_METRIKA_ID, isMetrikaLoaded } from "../lib/metrika";

/**
 * Sends a Yandex Metrika hit on client-side route changes.
 * The initial pageview is recorded by ym init, so it is skipped here.
 * No-op unless Metrika was loaded after cookie consent.
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
    if (!isMetrikaLoaded() || typeof window.ym !== "function") return;
    window.ym(YANDEX_METRIKA_ID, "hit", window.location.href, { referer });
  }, [location.pathname, location.search]);

  return null;
}
