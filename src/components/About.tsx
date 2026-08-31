import { company } from "../data";
import { publicUrl } from "../lib/publicUrl";
import type { Product } from "../data/types";

export function About({ photo }: { photo?: Product }) {
  return (
    <section className="section about-section" id="about">
      <div className="container about-grid">
        <div>
          <p className="eyebrow">О бренде</p>
          <h2 className="section-title">О компании</h2>
          <p className="section-lead">{company.about}</p>
          <ul className="facts">
            {company.facts.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </div>
        {photo?.images[0] ? (
          <div className="about-photo">
            <img src={publicUrl(photo.images[0])} alt={photo.name} width={640} height={800} />
          </div>
        ) : null}
      </div>
    </section>
  );
}
