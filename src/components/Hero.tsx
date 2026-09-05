import type { Product } from "../data/types";
import { contacts } from "../data";
import { publicUrl } from "../lib/publicUrl";

export function Hero({ photo }: { photo?: Product }) {
  return (
    <section className="hero" id="top">
      <div className="container hero-grid">
        <div className="hero-copy reveal">
          <p className="eyebrow">Эславия · опт и розница</p>
          <h1>
            Женский трикотаж <em>оптом и в розницу</em>
          </h1>
          <p className="hero-lead">
            Эславия — домашний трикотаж: платья, пижамы, сарафаны, халаты и сорочки. Розница — цены на сайте.
            Опт — по прайсу после заявки. Размеры от 42 до 70.
          </p>
          <div className="hero-actions">
            <a className="btn btn-primary" href="#wholesale">
              Получить оптовый прайс
            </a>
            <a className="btn btn-ghost" href="#catalog">
              Смотреть каталог
            </a>
            <a className="btn btn-ghost" href={contacts.whatsapp}>
              Написать в WhatsApp
            </a>
          </div>
        </div>
        {photo?.images[0] ? (
          <div className="hero-photo reveal">
            <img src={publicUrl(photo.images[0])} alt={photo.name} width={720} height={900} fetchPriority="high" />
          </div>
        ) : null}
      </div>
    </section>
  );
}
