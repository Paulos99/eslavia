import type { Category, Company, Contacts, Delivery, Product, SizeGuide } from "./types";
import productsJson from "@data/products.json";
import categoriesJson from "@data/categories.json";
import companyJson from "@data/company.json";
import contactsJson from "@data/contacts.json";
import sizeGuideJson from "@data/size-guide.json";
import deliveryJson from "@data/delivery.json";
import privacyMd from "@data/privacy.md?raw";

export const products = productsJson as Product[];
export const categories = categoriesJson as Category[];
export const company = companyJson as Company;
export const contacts = contactsJson as Contacts;
export const sizeGuide = sizeGuideJson as SizeGuide;
export const delivery = deliveryJson as Delivery;
export const privacyText = privacyMd as string;
