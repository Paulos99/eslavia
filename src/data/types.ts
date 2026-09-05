export type Product = {
  id: string;
  article: string;
  name: string;
  category: string;
  categories: string[];
  priceRetail: number | null;
  priceWholesale: number | null;
  sizes: string[];
  colors: string[];
  material: string | null;
  description: string | null;
  availability?: string | null;
  images: string[];
  sourceUrl?: string;
};

export type Category = {
  id: string;
  name: string;
  count: number;
  image: string | null;
};

export type Company = {
  name: string;
  legalName: string;
  tagline: string;
  about: string;
  facts: string[];
  inn: string;
  legalAddress: string;
  rknRegistryNumber: string;
  year: number;
};

export type Contacts = {
  phone: string;
  phoneRaw: string;
  email: string;
  address: string;
  whatsapp: string;
  viber: string;
  telegram: string;
};

export type SizeGuide = {
  note: string;
  columns: string[];
  rows: string[][];
};

export type Delivery = {
  pickup: string;
  carriers: string[];
  carrierPaidBy: string;
  toTerminal: string;
  payment: string;
  fullText: string;
};

export type YandexForm = {
  /** Ссылка из «Поделиться» или src из кода iframe. Пусто — запасной канал на почту. */
  embedUrl: string;
  height: number;
};
