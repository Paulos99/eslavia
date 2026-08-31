import { company, contacts, delivery } from "../data";

export function Contacts() {
  return (
    <section className="section" id="contacts">
      <div className="container contacts-grid">
        <div>
          <p className="eyebrow">Связь</p>
          <h2 className="section-title">Контакты</h2>
          <p className="section-lead">{contacts.address}</p>
          <div className="contact-lines">
            <a href={`tel:+${contacts.phoneRaw}`}>{contacts.phone}</a>
            <a href={`mailto:${contacts.email}`}>{contacts.email}</a>
            <span>ИНН {company.inn}</span>
          </div>
          <div className="hero-actions">
            <a className="btn btn-ghost" href={contacts.whatsapp}>
              WhatsApp
            </a>
            <a className="btn btn-ghost" href={contacts.telegram}>
              Telegram
            </a>
            <a className="btn btn-ghost" href={contacts.viber}>
              Viber
            </a>
          </div>
        </div>
        <div>
          <h3 className="section-title section-title-s">Доставка и оплата</h3>
          <ul className="facts">
            <li>Самовывоз: {delivery.pickup}</li>
            <li>
              Доставка ТК {delivery.carriers.join(", ")} — за счёт покупателя. До терминала — {delivery.toTerminal}.
            </li>
            <li>Оплата в точке выдачи транспортной компании или по адресу самовывоза.</li>
          </ul>
        </div>
      </div>
    </section>
  );
}
