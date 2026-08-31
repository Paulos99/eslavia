import { useCallback, useState } from "react";
import type { Product } from "../data/types";

export function useModal() {
  const [product, setProduct] = useState<Product | null>(null);
  const open = useCallback((p: Product) => setProduct(p), []);
  const close = useCallback(() => setProduct(null), []);
  return { product, open, close };
}
