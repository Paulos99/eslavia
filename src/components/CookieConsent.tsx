import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  OPEN_CONSENT_EVENT,
  clearMetrikaData,
  getConsent,
  isMetrikaLoaded,
  loadMetrika,
  setConsent,
} from "../lib/metrika";

export function CookieConsent() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const stored = getConsent();
    if (stored === "accepted") loadMetrika();
    else if (stored === null) setOpen(true);

    const reopen = () => setOpen(true);
    window.addEventListener(OPEN_CONSENT_EVENT, reopen);
    return () => window.removeEventListener(OPEN_CONSENT_EVENT, reopen);
  }, []);

  if (!open) return null;

  const accept = () => {
    setConsent("accepted");
    setOpen(false);
    loadMetrika();
  };

  const decline = () => {
    setConsent("declined");
    setOpen(false);
    clearMetrikaData();
    // Metrika cannot be unloaded from a running page; reload so it stops immediately.
    if (isMetrikaLoaded()) window.location.reload();
  };

  return (
    <div className="cookie-bar" role="region" aria-label="Согласие на cookie">
      <div className="cookie-bar-inner">
        <p className="cookie-bar-text">
          Мы используем cookie и Яндекс Метрику, чтобы анализировать посещаемость и улучшать сайт. Подробнее — в{" "}
          <Link to="/privacy">Политике конфиденциальности</Link>.
        </p>
        <div className="cookie-bar-actions">
          <button type="button" className="btn cookie-btn cookie-btn-accept" onClick={accept}>
            Принять
          </button>
          <button type="button" className="btn cookie-btn cookie-btn-decline" onClick={decline}>
            Отклонить
          </button>
        </div>
      </div>
    </div>
  );
}
