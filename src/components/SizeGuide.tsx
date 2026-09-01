import { sizeGuide } from "../data";

export function SizeGuide() {
  return (
    <section className="section" id="sizes">
      <div className="container">
        <p className="eyebrow">Подбор</p>
        <h2 className="section-title">Таблица размеров</h2>
        {sizeGuide.note ? <p className="section-lead">{sizeGuide.note}</p> : null}
        <p className="table-hint">Листайте таблицу в сторону</p>
        <div className="size-table-wrap">
          <table>
            <thead>
              <tr>
                {sizeGuide.columns.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sizeGuide.rows.map((row) => (
                <tr key={row.join("-")}>
                  {row.map((cell, i) => (
                    <td key={i}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
