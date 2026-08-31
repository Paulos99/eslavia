export function formatPrice(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "Цена по запросу";
  return `${new Intl.NumberFormat("ru-RU").format(value)} ₽`;
}
