import { useEffect } from "react";
import type { Product } from "../data/types";

/** Open product modal from ?product=<id> (used by wholesale PDF links). */
export function useProductDeepLink(products: Product[], open: (p: Product) => void) {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = (params.get("product") || "").trim().toLowerCase();
    if (!id) return;
    const found = products.find((p) => p.id.toLowerCase() === id);
    if (found) open(found);
  }, [products, open]);
}
