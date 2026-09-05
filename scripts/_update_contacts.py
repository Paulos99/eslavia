# -*- coding: utf-8 -*-
from pathlib import Path
import json
import re

ROOT = Path(r"C:\Users\user\Desktop\Организация\Проекты\КОДИНГ\таисия")

PHONE = "+7 (901) 694-01-48"
PHONE_RAW = "79016940148"
EMAIL = "shyisewing@yandex.ru"  # keep until replaced
LEGAL = "Индивидуальный предприниматель Шлыкова А.Г."
INN = "370202329400"
OGRNIP = "323370000044608"
PICKUPS = [
    "г. Иваново, ул. Ташкентская, д. 20",
    "г. Кохма, ул. Ивановская, 17 (ТЦ Кохомский)",
]
ADDRESS_LEAD = "Самовывоз: Иваново (Ташкентская, 20) и Кохма (Ивановская, 17, ТЦ Кохомский)"

# --- company.json ---
company = json.loads((ROOT / "data/company.json").read_text(encoding="utf-8"))
company["legalName"] = LEGAL
company["inn"] = INN
company["ogrnip"] = OGRNIP
(ROOT / "data/company.json").write_text(json.dumps(company, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# --- contacts.json ---
contacts = {
    "phone": PHONE,
    "phoneRaw": PHONE_RAW,
    "email": EMAIL,
    "address": ADDRESS_LEAD,
    "whatsapp": f"https://wa.me/{PHONE_RAW}",
    "viber": f"viber://chat?number={PHONE_RAW}",
    "telegram": f"https://t.me/+{PHONE_RAW}",
}
(ROOT / "data/contacts.json").write_text(json.dumps(contacts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# --- delivery.json ---
carriers = ["Деловые линии", "СДЭК", "ПЭК"]
pickup_join = "; ".join(PICKUPS)
delivery = {
    "pickup": pickup_join,
    "pickups": PICKUPS,
    "carriers": carriers,
    "carrierPaidBy": "покупатель",
    "toTerminal": "бесплатно",
    "payment": "В точке выдачи транспортной компании или по адресу самовывоза. Онлайн-оплата на сайте не подключена.",
    "fullText": (
        "Самовывоз Вы можете забрать Ваш заказ самостоятельно: "
        + "; ".join(PICKUPS)
        + " Доставка транспортными компаниями Доставка осуществляется во все регионы России транспортными компаниями "
        "(Деловые линии, СДЭК, ПЭК) за счет покупателя. До терминала транспортной компании доставка бесплатная. "
        "Услуги транспортной компании оплачиваются покупателем при получении товара. Оплата Оплатить товар можно "
        "в точке выдачи товара транспортной компании либо по адресу самовывоза. Онлайн-оплата на сайте не подключена."
    ),
}
(ROOT / "data/delivery.json").write_text(json.dumps(delivery, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# --- types.ts ---
types = (ROOT / "src/data/types.ts").read_text(encoding="utf-8")
if "ogrnip" not in types:
    types = types.replace("  inn: string;\n", "  inn: string;\n  ogrnip?: string;\n")
if "pickups" not in types:
    types = types.replace(
        "export type Delivery = {\n  pickup: string;\n",
        "export type Delivery = {\n  pickup: string;\n  pickups?: string[];\n",
    )
(ROOT / "src/data/types.ts").write_text(types, encoding="utf-8")

# --- Contacts.tsx ---
contacts_tsx = '''import { company, contacts, delivery } from "../data";

export function Contacts() {
  const pickups = delivery.pickups?.length ? delivery.pickups : [delivery.pickup];

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
            <span>{company.legalName}</span>
            <span>ИНН {company.inn}</span>
            {company.ogrnip ? <span>ОГРНИП {company.ogrnip}</span> : null}
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
            <li>
              Самовывоз:
              <ul className="facts nested-facts">
                {pickups.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            </li>
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
'''
(ROOT / "src/components/Contacts.tsx").write_text(contacts_tsx, encoding="utf-8")

# --- Footer: add OGRNIP ---
footer = (ROOT / "src/components/Footer.tsx").read_text(encoding="utf-8")
old_foot = "{company.name} © {company.year} · ИНН {company.inn} · реестр операторов ПДн № {company.rknRegistryNumber}"
new_foot = "{company.name} © {company.year} · ИНН {company.inn}" + (
    "{company.ogrnip ? ` · ОГРНИП ${company.ogrnip}` : \"\"} · реестр операторов ПДн № {company.rknRegistryNumber}"
)
# JSX-friendly version
new_foot_jsx = '''{company.name} © {company.year} · ИНН {company.inn}
            {company.ogrnip ? <> · ОГРНИП {company.ogrnip}</> : null} · реестр операторов ПДн № {company.rknRegistryNumber}'''
if old_foot in footer:
    footer = footer.replace(old_foot, new_foot_jsx)
    (ROOT / "src/components/Footer.tsx").write_text(footer, encoding="utf-8")
    print("footer updated")
else:
    print("footer pattern miss")

# --- privacy.md light update ---
priv_path = ROOT / "data/privacy.md"
priv = priv_path.read_text(encoding="utf-8")
priv = priv.replace("Шлыкова Марина Анатольевна", "Шлыкова А.Г.")
priv = priv.replace("370252109182", INN)
priv = priv.replace("+7 (963) 152-97-47", PHONE)
priv = priv.replace("79631529747", PHONE_RAW)
priv = priv.replace("г. Иваново, ул. Свободы, д. 13", "; ".join(PICKUPS))
priv = priv.replace("г. Иваново, ул. Свободы, д.13", "; ".join(PICKUPS))
priv_path.write_text(priv, encoding="utf-8")
print("privacy updated")

# --- CSS for nested facts if needed ---
css_candidates = list((ROOT / "src").rglob("*.css"))
print("css files", [str(p.relative_to(ROOT)) for p in css_candidates[:10]])
for css in css_candidates:
    text = css.read_text(encoding="utf-8")
    if ".facts" in text and "nested-facts" not in text:
        text += "\n.facts.nested-facts, .nested-facts {\n  margin: 0.4rem 0 0 1rem;\n  padding: 0;\n  list-style: disc;\n}\n.nested-facts li { margin: 0.15rem 0; }\n"
        css.write_text(text, encoding="utf-8")
        print("css nested", css.name)
        break

print("JSON/TSX done")