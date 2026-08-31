import { Link } from "react-router-dom";
import { privacyText } from "../data";
import { Header } from "./Header";
import { Footer } from "./Footer";

function privacyParagraphs(raw: string) {
  const text = raw.replace(/^\uFEFF/, "").replace(/\r\n/g, "\n").trim();
  const withoutHeading = text.replace(/^# .+\n+/, "");
  const parts = withoutHeading.split(/\n\n+/).map((p) => p.trim()).filter(Boolean);
  if (parts[0]?.startsWith("Политика в отношении обработки персональных данных")) {
    parts.shift();
  }
  return parts;
}

export function PrivacyPage() {
  const paragraphs = privacyParagraphs(privacyText);
  return (
    <>
      <Header />
      <main className="container privacy-page">
        <p className="privacy-back">
          <Link to="/">← На главную</Link>
        </p>
        <h1>Политика конфиденциальности</h1>
        {paragraphs.map((p) => (
          <p key={p.slice(0, 48)}>{p}</p>
        ))}
      </main>
      <Footer />
    </>
  );
}
