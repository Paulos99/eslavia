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
  tagline: string;
  about: string;
  facts: string[];
  inn: string;
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
