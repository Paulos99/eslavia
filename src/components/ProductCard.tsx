import { formatPrice } from "../lib/formatPrice";
import { catalogThumb, publicUrl } from "../lib/publicUrl";
import type { Product } from "../data/types";

function compactSizes(sizes: string[]) {
  if (sizes.length <= 6) return sizes.join(" · ");
  return `${sizes[0]}–${sizes[sizes.length - 1]}`;
}

export function ProductCard({ product, onOpen }: { product: Product; onOpen: (p: Product) => void }) {
  const img = product.images[0];
  const img2 = product.images[1];
  return (
    <button type="button" className="product-card" onClick={() => onOpen(product)}>
      <div className="product-media">
        {img ? (
          <img
            className="main"
            src={publicUrl(catalogThumb(img))}
            srcSet={`${publicUrl(catalogThumb(img))} 960w`}
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
            src={publicUrl(catalogThumb(img2))}
            srcSet={`${publicUrl(catalogThumb(img2))} 960w`}
            sizes="(max-width: 1024px) 50vw, 25vw"
            alt=""
            width={480}
            height={640}
            loading="lazy"
          />
        ) : null}
        <span className="product-more">Подробнее</span>
      </div>
      <div className="product-meta">
        <h3>{product.name}</h3>
        <p className="price">{formatPrice(product.priceRetail)}</p>
        <p className="sizes">{product.sizes.length ? compactSizes(product.sizes) : "\u00a0"}</p>
      </div>
    </button>
  );
}
