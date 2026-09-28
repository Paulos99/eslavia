import { useState } from "react";
import { formatPrice } from "../lib/formatPrice";
import { gridImage, thumbFallback, warmFullImage } from "../lib/thumbs";
import type { Product } from "../data/types";
import { ImageLightbox } from "./ImageLightbox";

function compactSizes(sizes: string[]) {
  if (sizes.length <= 6) return sizes.join(" · ");
  return `${sizes[0]}–${sizes[sizes.length - 1]}`;
}

export function ProductCard({
  product,
  onOpen,
  priority = false,
}: {
  product: Product;
  onOpen: (p: Product) => void;
  /** First row after a user filter change: fetch immediately instead of lazily. */
  priority?: boolean;
}) {
  const [zoomOpen, setZoomOpen] = useState(false);
  // Hover image is mounted only after the first hover, so it doesn't compete with covers.
  const [hovered, setHovered] = useState(false);
  const img = product.images[0];
  const img2 = product.images[1];
  const main = img ? gridImage(img) : null;
  const second = img2 && hovered ? gridImage(img2) : null;
  const warm = () => warmFullImage(img);
  return (
    <>
      <div
        className="product-card"
        onPointerEnter={(e) => {
          if (e.pointerType === "mouse") setHovered(true);
          warm();
        }}
        onTouchStart={warm}
        onFocus={warm}
      >
        <button
          type="button"
          className="product-media"
          aria-label={`Увеличить фото: ${product.name}`}
          onClick={() => {
            if (product.images.length) setZoomOpen(true);
            else onOpen(product);
          }}
        >
          {img && main ? (
            <img
              className="main"
              src={main.src}
              srcSet={main.srcSet || undefined}
              sizes={main.sizes}
              alt={`${product.name}, артикул ${product.article}`}
              width={480}
              height={640}
              loading={priority ? "eager" : "lazy"}
              fetchPriority={priority ? "high" : "auto"}
              decoding="async"
              onError={thumbFallback(img)}
            />
          ) : (
            <div className="no-photo">Нет фото</div>
          )}
          {img2 && second ? (
            <img
              className="second"
              src={second.src}
              srcSet={second.srcSet || undefined}
              sizes={second.sizes}
              alt=""
              width={480}
              height={640}
              decoding="async"
              onError={thumbFallback(img2)}
            />
          ) : null}
          <span className="product-zoom-hint" aria-hidden="true">
            Увеличить
          </span>
        </button>
        <button type="button" className="product-meta" onClick={() => onOpen(product)}>
          <h3>{product.name}</h3>
          <p className="price">{formatPrice(product.priceRetail)}</p>
          <p className="sizes">{product.sizes.length ? compactSizes(product.sizes) : "\u00a0"}</p>
          <span className="product-more-inline">Подробнее</span>
        </button>
      </div>
      {zoomOpen && product.images.length ? (
        <ImageLightbox images={product.images} alt={product.name} onClose={() => setZoomOpen(false)} />
      ) : null}
    </>
  );
}
