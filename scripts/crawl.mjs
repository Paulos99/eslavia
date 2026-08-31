/**
 * Phase 1: crawl taisiy.ru (OpenCart) into data/raw/
 * No invented fields. Missing values stay null / [].
 */
import { mkdir, writeFile } from "node:fs/promises";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const RAW = join(ROOT, "data", "raw");
const BASE = "https://taisiy.ru";
const UA = "Mozilla/5.0 (compatible; TaisiyaCatalogAudit/1.0)";

const CATEGORY_URLS = [
  { slug: "katalog", url: `${BASE}/katalog`, name: "Каталог" },
  { slug: "kostyumy", url: `${BASE}/katalog/kostyumy`, name: "Костюмы" },
  { slug: "pizhamy", url: `${BASE}/katalog/pizhamy`, name: "Пижамы для дома" },
  { slug: "platjya", url: `${BASE}/katalog/platjya`, name: "Платья" },
  { slug: "sarafany", url: `${BASE}/katalog/sarafany`, name: "Сарафаны" },
  { slug: "tolstovki", url: `${BASE}/katalog/tolstovki`, name: "Толстовки" },
  { slug: "tuniki", url: `${BASE}/katalog/tuniki`, name: "Туники" },
  { slug: "vodolazki", url: `${BASE}/vodolazki`, name: "Водолазки" },
  { slug: "sorochki", url: `${BASE}/sorochki`, name: "Сорочки" },
  { slug: "futbolki", url: `${BASE}/futbolki`, name: "Футболки" },
  { slug: "khalaty", url: `${BASE}/khalaty`, name: "Халаты" },
  { slug: "velosipedki", url: `${BASE}/velosipedki`, name: "Велосипедки" },
  { slug: "topy", url: `${BASE}/topy`, name: "Топы" },
];

const INFO_PAGES = [
  { id: "home", url: `${BASE}/` },
  { id: "about", url: `${BASE}/about_us` },
  { id: "delivery", url: `${BASE}/delivery` },
  { id: "privacy", url: `${BASE}/privacy` },
  { id: "size-guide", url: `${BASE}/tablica-razmerov` },
  { id: "contact", url: `${BASE}/contact` },
  { id: "sitemap", url: `${BASE}/sitemap` },
  { id: "return", url: `${BASE}/return-add` },
  { id: "search", url: `${BASE}/index.php?route=product/search&search=&limit=100` },
];

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function fetchText(url) {
  const res = await fetch(url, { headers: { "User-Agent": UA, Accept: "text/html" } });
  const html = await res.text();
  return { status: res.status, url: res.url, html };
}

function decodeHtml(s) {
  return s
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();
}

function stripTags(html) {
  return decodeHtml(html.replace(/<br\s*\/?>/gi, "\n").replace(/<[^>]+>/g, " "));
}

function cacheToOriginal(url) {
  if (!url) return null;
  let u = url.split("?")[0];
  u = u.replace("/image/cache/", "/image/");
  u = u.replace(/-(\d+)x(\d+)(\.(jpe?g|png|webp|gif))$/i, "$3");
  return u;
}

function unique(arr) {
  return [...new Set(arr.filter(Boolean))];
}

function extractProductLinks(html) {
  const links = [];
  const re = /<div class="product-thumb">[\s\S]*?<h4><a href="([^"]+)">([\s\S]*?)<\/a><\/h4>/g;
  let m;
  while ((m = re.exec(html))) {
    const href = m[1].replace(/&amp;/g, "&").split("?")[0];
    links.push({ url: href, name: decodeHtml(m[2]) });
  }
  return links;
}

function extractPaginationPages(html, baseUrl) {
  const pages = new Set([baseUrl]);
  const re = /href="(https:\/\/taisiy\.ru\/[^"]*(?:[?&]page=\d+)[^"]*)"/g;
  let m;
  while ((m = re.exec(html))) {
    pages.add(m[1].replace(/&amp;/g, "&"));
  }
  const shown = html.match(/Показано с \d+ по \d+ из (\d+)/);
  const total = shown ? Number(shown[1]) : null;
  return { pages: [...pages], total };
}

function parseProduct(html, url) {
  const nameMatch = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/);
  const name = nameMatch ? decodeHtml(nameMatch[1]) : null;

  const articleMatch = html.match(/<li><b>Модель:<\/b>\s*([^<]+)<\/li>/);
  const article = articleMatch ? decodeHtml(articleMatch[1]) : null;

  const availabilityMatch = html.match(/<li><b>Наличие:<\/b>\s*([^<]+)<\/li>/);
  const availability = availabilityMatch ? decodeHtml(availabilityMatch[1]) : null;

  const idMatch = html.match(/wishlist\.add\('(\d+)'\)/);
  const ocId = idMatch ? idMatch[1] : null;

  const retailMatch = html.match(/data-price="([\d.]+)"\s+class="calc-price"/);
  const priceRetail = retailMatch ? Number(retailMatch[1]) : null;

  const wholesaleMatch = html.match(/<span class="opt-chena">([^<]+)<\/span>/);
  let priceWholesale = null;
  if (wholesaleMatch) {
    const n = wholesaleMatch[1].replace(/[^\d.,]/g, "").replace(",", ".");
    priceWholesale = n ? Number(n) : null;
  }

  const sizes = [];
  const sizeBlock = html.match(/<label class="control-label">Размер<\/label>([\s\S]*?)<\/div>\s*<\/div>/);
  if (sizeBlock) {
    const sizeRe = /<label for="\d+">\s*([^<]+?)\s*<\/label>/g;
    let sm;
    while ((sm = sizeRe.exec(sizeBlock[1]))) {
      const s = decodeHtml(sm[1]);
      if (s) sizes.push(s);
    }
  }

  const descMatch = html.match(/id="tab-description">([\s\S]*?)<\/div>/);
  const description = descMatch ? stripTags(descMatch[1]).replace(/\n+/g, "\n").trim() : null;

  const material = extractMaterial(description);

  const imageUrls = [];
  const imgRe = /<a class="thumbnail" href="(https:\/\/taisiy\.ru\/image\/cache\/[^"]+)"/g;
  let im;
  while ((im = imgRe.exec(html))) {
    imageUrls.push(im[1]);
  }

  const breadcrumbs = [];
  const bcRe = /<ul class="breadcrumb">[\s\S]*?<\/ul>/;
  const bc = html.match(bcRe);
  if (bc) {
    const aRe = /<a href="[^"]*">([\s\S]*?)<\/a>/g;
    let bm;
    while ((bm = aRe.exec(bc[0]))) {
      breadcrumbs.push(decodeHtml(bm[1].replace(/<[^>]+>/g, "")));
    }
  }

  return {
    sourceUrl: url,
    ocId,
    name,
    article,
    availability,
    priceRetail,
    priceWholesale,
    sizes: unique(sizes),
    colors: [],
    material,
    description: description || null,
    imageCacheUrls: unique(imageUrls),
    imageOriginalCandidates: unique(imageUrls.map(cacheToOriginal)),
    breadcrumbs,
  };
}

function extractMaterial(description) {
  if (!description) return null;
  const m =
    description.match(/ткань\s+100%\s*хлопок/i) ||
    description.match(/из\s+100%\s*хлопка/i) ||
    description.match(/100%\s*хлопок/i) ||
    description.match(/из\s+натурального\s+хлопка/i) ||
    description.match(/из\s+кулирки/i);
  if (!m) return null;
  const t = m[0].toLowerCase();
  if (t.includes("кулирк")) return "кулирка";
  if (t.includes("хлоп")) return "100% хлопок";
  return m[0];
}

function parseSizeTable(html) {
  const rows = [];
  const table = html.match(/<table[\s\S]*?<\/table>/i);
  if (!table) return rows;
  const trRe = /<tr[\s\S]*?<\/tr>/gi;
  const trs = table[0].match(trRe) || [];
  for (const tr of trs) {
    const cells = [...tr.matchAll(/<t[dh][^>]*>([\s\S]*?)<\/t[dh]>/gi)].map((c) =>
      decodeHtml(c[1].replace(/<[^>]+>/g, " "))
    );
    if (cells.length) rows.push(cells);
  }
  return rows;
}

function parseCategoryFilters(html) {
  const filters = { sizes: [], materials: [], colors: [], manufacturers: [], priceRange: null };
  const sizeSec = html.match(/Размер[\s\S]*?(?=<div class="filter-group"|Материал|Производитель|Цвет|Сбросить|$)/);
  // Simpler: grab filter labels near known headings
  const colorBlock = html.match(/>Цвет<\/[a-z]+>([\s\S]*?)(?:Сбросить|<\/form>)/i);
  if (colorBlock) {
    const names = colorBlock[1].matchAll(/>([а-яёa-z\- ]+)\s+\d+\s*</gi);
    for (const n of names) filters.colors.push(decodeHtml(n[1]));
  }
  const matBlock = html.match(/>Материал<\/[a-z]+>([\s\S]*?)(?:Производитель|Цвет|Сбросить)/i);
  if (matBlock) {
    const names = matBlock[1].matchAll(/>([^<]+?)\s+\d+\s*</g);
    for (const n of names) filters.materials.push(decodeHtml(n[1]));
  }
  return filters;
}

function extractCategoryNav(html) {
  const cats = [];
  const re = /<a href="(https:\/\/taisiy\.ru\/katalog\/[^"]+)"[^>]*>[\s\-]*([^<]+)</g;
  let m;
  while ((m = re.exec(html))) {
    cats.push({ url: m[1], name: decodeHtml(m[2]) });
  }
  const extra = html.matchAll(/<li><a href="(https:\/\/taisiy\.ru\/[^"]+)">\s*-\s*([^<]+)</g);
  for (const e of extra) {
    cats.push({ url: e[1], name: decodeHtml(e[2]) });
  }
  const seen = new Set();
  return cats.filter((c) => {
    if (seen.has(c.url)) return false;
    seen.add(c.url);
    return true;
  });
}

async function crawlCategory(cat) {
  const first = await fetchText(cat.url);
  await mkdir(join(RAW, "categories"), { recursive: true });
  await writeFile(join(RAW, "categories", `${cat.slug}.html`), first.html, "utf8");

  if (first.status >= 400 || /не найдена|нет товаров/i.test(first.html)) {
    const empty = /нет товаров/i.test(first.html);
    return {
      ...cat,
      status: first.status,
      empty: empty || first.status >= 400,
      productCountListed: 0,
      products: [],
      pagesFetched: 1,
    };
  }

  const { pages, total } = extractPaginationPages(first.html, cat.url);
  let allHtml = first.html;
  const extraPages = pages.filter((p) => p !== cat.url && /[?&]page=\d+/.test(p));
  extraPages.sort((a, b) => {
    const pa = Number((a.match(/[?&]page=(\d+)/) || [])[1] || 0);
    const pb = Number((b.match(/[?&]page=(\d+)/) || [])[1] || 0);
    return pa - pb;
  });

  for (const p of extraPages) {
    await sleep(250);
    const next = await fetchText(p);
    const pageNum = (p.match(/[?&]page=(\d+)/) || [])[1] || "x";
    await writeFile(join(RAW, "categories", `${cat.slug}-p${pageNum}.html`), next.html, "utf8");
    allHtml += "\n" + next.html;
  }

  const products = extractProductLinks(allHtml);
  const seen = new Set();
  const uniq = products.filter((p) => {
    if (seen.has(p.url)) return false;
    seen.add(p.url);
    return true;
  });

  return {
    ...cat,
    status: first.status,
    empty: uniq.length === 0,
    productCountListed: total,
    productCountFound: uniq.length,
    products: uniq,
    pagesFetched: 1 + extraPages.length,
    nav: extractCategoryNav(first.html),
  };
}

async function main() {
  await mkdir(RAW, { recursive: true });
  await mkdir(join(RAW, "products"), { recursive: true });
  await mkdir(join(RAW, "pages"), { recursive: true });

  const pages = {};
  for (const p of INFO_PAGES) {
    console.log("page", p.id, p.url);
    const r = await fetchText(p.url);
    await writeFile(join(RAW, "pages", `${p.id}.html`), r.html, "utf8");
    pages[p.id] = { url: p.url, status: r.status, finalUrl: r.url, bytes: r.html.length };
    await sleep(200);
  }

  const categories = [];
  const productIndex = new Map();

  for (const cat of CATEGORY_URLS) {
    console.log("category", cat.slug);
    const crawled = await crawlCategory(cat);
    categories.push(crawled);
    for (const p of crawled.products || []) {
      if (!productIndex.has(p.url)) {
        productIndex.set(p.url, { url: p.url, name: p.name, categories: [crawled.name] });
      } else {
        const rec = productIndex.get(p.url);
        if (!rec.categories.includes(crawled.name)) rec.categories.push(crawled.name);
      }
    }
    await sleep(250);
  }

  // Search results as completeness source
  const searchHtml = await (await import("node:fs/promises")).readFile(join(RAW, "pages", "search.html"), "utf8");
  for (const p of extractProductLinks(searchHtml)) {
    if (!productIndex.has(p.url)) {
      productIndex.set(p.url, { url: p.url, name: p.name, categories: ["(только поиск)"] });
    }
  }

  const products = [];
  let i = 0;
  for (const rec of productIndex.values()) {
    i += 1;
    console.log(`product ${i}/${productIndex.size}`, rec.url);
    const r = await fetchText(rec.url);
    const slug = rec.url.replace(BASE + "/", "").replace(/[^\w\-а-яё]+/gi, "_") || `p${i}`;
    await writeFile(join(RAW, "products", `${slug}.html`), r.html, "utf8");
    const parsed = parseProduct(r.html, rec.url);
    parsed.listedName = rec.name;
    parsed.listedCategories = rec.categories.filter((c) => c !== "Каталог");
    products.push(parsed);
    await sleep(200);
  }

  const sizeHtml = await (await import("node:fs/promises")).readFile(join(RAW, "pages", "size-guide.html"), "utf8");
  const aboutHtml = await (await import("node:fs/promises")).readFile(join(RAW, "pages", "about.html"), "utf8");
  const deliveryHtml = await (await import("node:fs/promises")).readFile(join(RAW, "pages", "delivery.html"), "utf8");
  const privacyHtml = await (await import("node:fs/promises")).readFile(join(RAW, "pages", "privacy.html"), "utf8");
  const contactHtml = await (await import("node:fs/promises")).readFile(join(RAW, "pages", "contact.html"), "utf8");

  const dump = {
    crawledAt: new Date().toISOString(),
    source: BASE,
    pages,
    categories: categories.map((c) => ({
      slug: c.slug,
      name: c.name,
      url: c.url,
      status: c.status,
      empty: c.empty,
      productCountListed: c.productCountListed,
      productCountFound: c.productCountFound,
      pagesFetched: c.pagesFetched,
      products: c.products,
    })),
    products,
    sizeTable: parseSizeTable(sizeHtml),
    aboutText: stripTags((aboutHtml.match(/id="content"[\s\S]*?<h1[\s\S]*?<\/h1>([\s\S]*?)<footer/) || [])[1] || ""),
    deliveryText: stripTags((deliveryHtml.match(/id="content"[\s\S]*?<h1[\s\S]*?<\/h1>([\s\S]*?)<footer/) || [])[1] || ""),
    privacyText: stripTags((privacyHtml.match(/id="content"[\s\S]*?<h1[\s\S]*?<\/h1>([\s\S]*?)<footer/) || [])[1] || ""),
    contactHtmlExcerpt: stripTags((contactHtml.match(/id="content"[\s\S]*?<h1[\s\S]*?<\/h1>([\s\S]*?)Форма обратной связи/) || [])[1] || ""),
  };

  await writeFile(join(RAW, "crawl-dump.json"), JSON.stringify(dump, null, 2), "utf8");
  console.log("DONE products:", products.length, "categories:", categories.length);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
