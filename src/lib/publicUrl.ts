export function publicUrl(path: string): string {
  if (!path) return path;
  const base = import.meta.env.BASE_URL;
  if (path.startsWith("/")) return `${base}${path.slice(1)}`;
  return path;
}

/** Catalog grid preview: 01.webp → 01-card.webp */
export function catalogThumb(path: string): string {
  const i = path.lastIndexOf(".");
  if (i < 0) return path;
  return `${path.slice(0, i)}-card${path.slice(i)}`;
}
