import { useState } from "react";
import { formatPrice } from "../lib/formatPrice";
import { publicUrl } from "../lib/publicUrl";
import type { Product } from "../data/types";
import { ImageLightbox } from "./ImageLightbox";

function compactSizes(sizes: string[]) {
  if (sizes.length <= 6) return sizes.join(" · ");
  return `${sizes[0]}–${sizes[sizes.length - 1]}`;
}

export function ProductCard({ product, onOpen }: { product: Product; onOpen: (p: Product) => void }) {
  const [zoomOpen, setZoomOpen] = useState(false);
  const img = product.images[0];
  const img2 = product.images[1];
  return (
    <>
      <div className="product-card">
        <button
          type="button"
          className="product-media"
          aria-label={`Увеличить фото: ${product.name}`}
          onClick={() => {
            if (product.images.length) setZoomOpen(true);
            else onOpen(product);
          }}
        >
          {img ? (
            <img
              className="main"
              src={publicUrl(img)}
              srcSet={`${publicUrl(img)} 960w`}
              sizes="(max-width: 1024px) 50vw, 25vw"
              alt={`${product.name}, артикул ${product.article}`}
              width={480}
              height={640}
              loading="lazy"
            />
          ) : (
            <div className="no-photo">Нет фото</div>
          )}
          {img2 ? (
            <img
              className="second"
              src={publicUrl(img2)}
              srcSet={`${publicUrl(img2)} 960w`}
              sizes="(max-width: 1024px) 50vw, 25vw"
              alt=""
              width={480}
              height={640}
              loading="lazy"
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
