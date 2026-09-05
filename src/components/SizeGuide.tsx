import { useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { ChevronDown } from "lucide-react";
import { sizeGuide } from "../data";

export function SizeGuide() {
  const [open, setOpen] = useState(false);
  const tableRef = useRef<HTMLTableElement>(null);
  const [collapsedH, setCollapsedH] = useState(48);

  useLayoutEffect(() => {
    const table = tableRef.current;
    if (!table) return;
    const measure = () => {
      setCollapsedH(Math.max(40, Math.round(table.scrollHeight * 0.1)));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(table);
    return () => ro.disconnect();
  }, []);

  return (
    <section className="section" id="sizes">
      <div className="container">
        <p className="eyebrow">Подбор</p>
        <h2 className="section-title">Таблица размеров</h2>
        {sizeGuide.note ? <p className="section-lead">{sizeGuide.note}</p> : null}
        {open ? <p className="table-hint">Листайте таблицу в сторону</p> : null}
        <div
          className={`size-table-fold${open ? " is-open" : ""}`}
          style={{ "--size-table-collapsed": `${collapsedH}px` } as CSSProperties}
        >
          <div className="size-table-wrap">
            <table id="size-table" ref={tableRef}>
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
          <button
            type="button"
            className="size-table-toggle"
            aria-expanded={open}
            aria-controls="size-table"
            aria-label={open ? "Свернуть таблицу размеров" : "Раскрыть таблицу размеров"}
            onClick={() => setOpen((v) => !v)}
          >
            <ChevronDown size={22} strokeWidth={1.75} aria-hidden="true" />
          </button>
        </div>
      </div>
    </section>
  );
}
