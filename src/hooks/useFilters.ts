import { useMemo, useState } from "react";
import type { Product } from "../data/types";

export function useFilters(products: Product[]) {
  const [category, setCategory] = useState<string | null>(null);
  const [size, setSize] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const sizes = useMemo(() => {
    const set = new Set<string>();
    products.forEach((p) => p.sizes.forEach((s) => set.add(s)));
    return [...set].sort((a, b) => Number(a) - Number(b));
  }, [products]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return products.filter((p) => {
      if (category && p.category !== category) return false;
      if (size && !p.sizes.includes(size)) return false;
      if (q) {
        const hay = `${p.name} ${p.article} ${p.category}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [products, category, size, query]);

  return { category, setCategory, size, setSize, query, setQuery, sizes, filtered };
}
