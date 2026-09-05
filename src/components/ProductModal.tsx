import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { formatPrice } from "../lib/formatPrice";
import { publicUrl } from "../lib/publicUrl";
import type { Product } from "../data/types";
import { ImageLightbox } from "./ImageLightbox";

export function ProductModal({ product, onClose }: { product: Product; onClose: () => void }) {
  const [index, setIndex] = useState(0);
  const [zoomOpen, setZoomOpen] = useState(false);
  const zoomOpenRef = useRef(false);
  zoomOpenRef.current = zoomOpen;
  const closeRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIndex(0);
    setZoomOpen(false);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (zoomOpenRef.current) return;
        onClose();
      }
      if (e.key !== "Tab" || !dialogRef.current) return;
      const nodes = [...dialogRef.current.querySelectorAll<HTMLElement>("a[href], button, input, select, textarea")].filter(
        (el) => !el.hasAttribute("disabled"),
      );
      if (!nodes.length) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [product, onClose]);

  const img = product.images[index] || product.images[0];

  return (
    <div className="modal-root" role="dialog" aria-modal="true" aria-labelledby="product-title">
      <button className="modal-backdrop" type="button" aria-label="Закрыть" onClick={onClose} />
      <div className="modal-dialog" ref={dialogRef}>
        <button ref={closeRef} className="drawer-close" type="button" aria-label="Закрыть" onClick={onClose}>
          <X size={20} />
        </button>
        <div className="modal-gallery">
          {img ? (
            <button
              type="button"
              className="modal-main-photo"
              aria-label="Увеличить фото"
              onClick={() => setZoomOpen(true)}
            >
              <img src={publicUrl(img)} alt={product.name} width={800} height={1000} />
            </button>
          ) : (
            <div className="no-photo">Нет фото</div>
          )}
          {product.images.length > 1 ? (
            <div className="thumbs">
              {product.images.map((src, i) => (
                <button
                  key={src}
                  type="button"
                  className={i === index ? "is-active" : ""}
                  onClick={() => setIndex(i)}
                  aria-label={`Фото ${i + 1}`}
                >
                  <img src={publicUrl(src)} alt="" width={56} height={70} loading={Math.abs(i - index) > 1 ? "lazy" : "eager"} />
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <div className="modal-info">
          <p className="eyebrow">{product.category}</p>
          <h2 id="product-title">{product.name}</h2>
          <p className="article">Артикул {product.article}</p>
          <p className="modal-price">{formatPrice(product.priceRetail)}</p>
          {product.sizes.length ? (
            <p className="modal-spec">
              <span>Размеры</span>
              {product.sizes.join("  ·  ")}
            </p>
          ) : null}
          {product.material ? (
            <p className="modal-spec">
              <span>Материал</span>
              {product.material}
            </p>
          ) : null}
          {product.description ? <p className="modal-desc">{product.description}</p> : null}
          <a className="btn btn-primary" href={publicUrl("/#wholesale")} onClick={onClose}>
            Получить оптовый прайс
          </a>
        </div>
      </div>
      {zoomOpen && product.images.length ? (
        <ImageLightbox
          images={product.images}
          startIndex={index}
          alt={product.name}
          onClose={() => setZoomOpen(false)}
        />
      ) : null}
    </div>
  );
}
