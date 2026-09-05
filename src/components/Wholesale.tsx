import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, FileDown } from "lucide-react";
import { submitLead } from "../lib/submitLead";
import { publicUrl } from "../lib/publicUrl";
import { validateLeadContact } from "../lib/leadContact";

export function Wholesale() {
  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState(false);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!consent) {
      setError("Нужно согласие на обработку персональных данных");
      return;
    }
    const contactCheck = validateLeadContact(contact);
    if (!contactCheck.ok) {
      setError(contactCheck.error);
      return;
    }
    setPending(true);
    try {
      const result = await submitLead({ name, contact, consent });
      if (!result.ok) {
        setOk(false);
        setError(result.error || "Не удалось отправить заявку");
        return;
      }
      setOk(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="wholesale" id="wholesale">
      <div className="container">
        <div className="wholesale-box">
          <div>
            <p className="eyebrow">Для оптовиков</p>
            <h2 className="section-title">Покупаете одежду оптом?</h2>
            <p className="section-lead">Получите актуальный оптовый прайс и информацию для заказа. Скидки при сумме заказа от 5000 ₽.</p>
          </div>
          {ok ? (
            <div className="success-box" role="status" aria-live="polite">
              <CheckCircle2 className="success-icon" size={28} strokeWidth={1.6} aria-hidden />
              <h3 className="section-title section-title-s">Контакт отправлен</h3>
              <p className="success-lead">Заявка уже у нас. Мы свяжемся с вами и подтвердим условия заказа.</p>
              <a className="btn btn-light" href={publicUrl("/prices/optovyy-prays.pdf")} download="optovyy-prays-eslavia.pdf">
                <FileDown size={16} strokeWidth={1.8} aria-hidden />
                Скачать оптовый прайс
              </a>
              <p className="success-note">Актуальные условия и наличие подтвердим при заказе.</p>
            </div>
          ) : (
            <form className="form" onSubmit={onSubmit}>
              <label className="field">
                <span>Имя</span>
                <input value={name} onChange={(e) => setName(e.target.value)} required autoComplete="name" />
              </label>
              <label className="field">
                <span>Телефон / Telegram / e-mail</span>
                <input
                  value={contact}
                  onChange={(e) => setContact(e.target.value)}
                  required
                  autoComplete="tel"
                  inputMode="tel"
                  placeholder="+7 999 123-45-67"
                />
              </label>
              <label className="checkbox">
                <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} required />
                <span>
                  Я согласен(на) на обработку персональных данных (имя и контакт) для связи и направления оптового прайса.{" "}
                  <Link to="/privacy">Политика конфиденциальности</Link>
                </span>
              </label>
              {error ? <p className="form-error">{error}</p> : null}
              <button className="btn btn-light" type="submit" disabled={pending || !consent}>
                {pending ? "Отправка…" : "Получить прайс"}
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}
