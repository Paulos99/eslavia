import { useEffect } from "react";

/**
 * SPA-friendly deep links: on first load, scroll to the element named by
 * location.hash (e.g. /#price-form). The browser's native fragment scroll
 * runs before React renders, and lazy images shift layout afterwards, so we
 * re-align for a short while and stop as soon as the user interacts.
 * If the target and its section heading fit on screen together, the section
 * top is aligned instead, so the heading stays visible above a form.
 */
export function useHashScroll() {
  useEffect(() => {
    const id = decodeURIComponent(window.location.hash.slice(1));
    if (!id) return;
    let stopped = false;
    const timers: number[] = [];
    const align = () => {
      if (stopped) return;
      const el = document.getElementById(id);
      if (!el) return;
      const margin = parseFloat(getComputedStyle(el).scrollMarginTop) || 0;
      const box = el.getBoundingClientRect();
      // Show the surrounding section heading too when it fits with the target.
      const section = el.closest("section");
      const sTop = section && section !== el ? section.getBoundingClientRect().top : null;
      const fits = sTop !== null && box.bottom - sTop + margin <= window.innerHeight;
      const top = (fits ? (sTop as number) : box.top) - margin;
      if (Math.abs(top) > 2) window.scrollTo({ top: window.scrollY + top, behavior: "instant" as ScrollBehavior });
    };
    const stop = () => {
      stopped = true;
    };
    const events = ["wheel", "touchstart", "keydown", "mousedown"] as const;
    events.forEach((e) => window.addEventListener(e, stop, { passive: true, once: true }));
    requestAnimationFrame(align);
    [150, 400, 800, 1500, 2500].forEach((ms) => timers.push(window.setTimeout(align, ms)));
    window.addEventListener("load", align, { once: true });
    return () => {
      stopped = true;
      timers.forEach((t) => window.clearTimeout(t));
      events.forEach((e) => window.removeEventListener(e, stop));
      window.removeEventListener("load", align);
    };
  }, []);
}
