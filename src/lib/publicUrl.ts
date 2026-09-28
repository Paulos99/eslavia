export function publicUrl(path: string): string {
  if (!path) return path;
  const base = import.meta.env.BASE_URL;
  if (path.startsWith("/")) return `${base}${path.slice(1)}`;
  return path;
}
