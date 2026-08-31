import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { contacts } from "../data";
import { publicUrl } from "../lib/publicUrl";

const links = [
  { href: "/#catalog", label: "Каталог" },
  { href: "/#about", label: "О компании" },
  { href: "/#wholesale", label: "Оптовым покупателям" },
  { href: "/#contacts", label: "Контакты" },
];

export function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <>
      <div className="topbar">
        <div className="container topbar-inner">
          <span>Иваново · опт и розница</span>
          <a href={`tel:+${contacts.phoneRaw}`}>{contacts.phone}</a>
        </div>
      </div>
      <header className={`header ${scrolled ? "is-scrolled" : ""}`}>
        <div className="container header-inner">
          <a className="logo" href={publicUrl("/#top")} aria-label="Эславия — на главную">
            <img src={publicUrl("/brand/logo.svg")} alt="Эславия" width={220} height={52} />
          </a>
          <nav className="nav" aria-label="Основная">
            {links.map((l) => (
              <a key={l.href} href={publicUrl(l.href)}>
                {l.label}
              </a>
            ))}
          </nav>
          <div className="header-actions">
            <a className="btn btn-primary header-cta" href={publicUrl("/#wholesale")}>
              Получить оптовый прайс
            </a>
            <button className="menu-btn" type="button" aria-label={open ? "Закрыть меню" : "Открыть меню"} onClick={() => setOpen(!open)}>
              {open ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>
        {open ? (
          <div className="container mobile-nav">
            {links.map((l) => (
              <a key={l.href} href={publicUrl(l.href)} onClick={() => setOpen(false)}>
                {l.label}
              </a>
            ))}
            <a className="btn btn-primary" href={publicUrl("/#wholesale")} onClick={() => setOpen(false)}>
              Получить оптовый прайс
            </a>
          </div>
        ) : null}
      </header>
    </>
  );
}
