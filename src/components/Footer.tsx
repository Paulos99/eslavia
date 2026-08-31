import { Link } from "react-router-dom";
import { company, contacts } from "../data";
import { publicUrl } from "../lib/publicUrl";

export function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-grid">
        <div>
          <div className="logo">
            <img src={publicUrl("/brand/logo.svg")} alt="Эславия" width={220} height={52} />
          </div>
          <p className="footer-tagline">{company.tagline}</p>
        </div>
        <nav className="footer-col" aria-label="Подвал">
          <p className="footer-heading">Разделы</p>
          <a href={publicUrl("/#catalog")}>Каталог</a>
          <a href={publicUrl("/#about")}>О компании</a>
          <a href={publicUrl("/#wholesale")}>Оптовым покупателям</a>
          <Link to="/privacy">Политика конфиденциальности</Link>
        </nav>
        <div className="footer-col">
          <p className="footer-heading">Контакты</p>
          <a href={`tel:+${contacts.phoneRaw}`}>{contacts.phone}</a>
          <a href={`mailto:${contacts.email}`}>{contacts.email}</a>
          <span>{contacts.address}</span>
        </div>
        <div className="footer-col">
          <p className="footer-heading">Мессенджеры</p>
          <a href={contacts.whatsapp}>WhatsApp</a>
          <a href={contacts.telegram}>Telegram</a>
          <a href={contacts.viber}>Viber</a>
        </div>
      </div>
      <div className="container footer-bottom">
        <p>
          {company.name} © {company.year} · ИНН {company.inn}
        </p>
      </div>
    </footer>
  );
}
