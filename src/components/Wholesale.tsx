import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { submitLead } from "../lib/submitLead";
import { publicUrl } from "../lib/publicUrl";

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
    setPending(true);
    const result = await submitLead({ name, contact, consent });
    setPending(false);
    if (!result.ok) {
      setOk(false);
      setError(result.error || "Не удалось отправить заявку");
      return;
    }
    setOk(true);
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
            <div className="success-box">
              <h3 className="section-title section-title-s">Спасибо!</h3>
              <p className="success-lead">Прайс готов.</p>
              <a className="btn btn-light" href={publicUrl("/prices/optovyy-prays.pdf")} download>
                Скачать оптовый прайс
              </a>
            </div>
          ) : (
            <form className="form" onSubmit={onSubmit}>
              <label className="field">
                <span>Имя</span>
                <input value={name} onChange={(e) => setName(e.target.value)} required autoComplete="name" />
              </label>
              <label className="field">
                <span>Телефон / Telegram / e-mail</span>
                <input value={contact} onChange={(e) => setContact(e.target.value)} required autoComplete="tel" />
              </label>
              <label className="checkbox">
                <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} required />
                <span>
                  Я согласен(на) на обработку персональных данных.{" "}
                  <Link to="/privacy">Политика конфиденциальности</Link>
                </span>
              </label>
              {error ? <p className="form-error">{error}</p> : null}
              <button className="btn btn-light" type="submit" disabled={pending}>
                {pending ? "Отправка…" : "Получить прайс"}
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}
