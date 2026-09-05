import { Header } from "./components/Header";
import { Hero } from "./components/Hero";
import { FactsBar } from "./components/FactsBar";
import { CategoryNav } from "./components/CategoryNav";
import { Catalog } from "./components/Catalog";
import { ProductModal } from "./components/ProductModal";
import { About } from "./components/About";
import { Wholesale } from "./components/Wholesale";
import { SizeGuide } from "./components/SizeGuide";
import { Contacts } from "./components/Contacts";
import { SeoFaq } from "./components/SeoFaq";
import { Footer } from "./components/Footer";
import { categories, products } from "./data";
import { useFilters } from "./hooks/useFilters";
import { useModal } from "./hooks/useModal";

export function HomePage() {
  const filters = useFilters(products);
  const modal = useModal();
  const withPhotos = products.filter((p) => p.images.length);
  const heroPhoto =
    withPhotos.find((p) => p.id === "m-105h") ||
    withPhotos.find((p) => p.category === "Платья") ||
    withPhotos[0];
  const aboutPhoto =
    withPhotos.find((p) => p.id === "m-101c") ||
    withPhotos.find((p) => p.category === "Платья") ||
    withPhotos[1] ||
    withPhotos[0];

  return (
    <>
      <a className="skip-link" href="#catalog">
        К каталогу
      </a>
      <Header />
      <main>
        <Hero photo={heroPhoto} />
        <FactsBar />
        <CategoryNav
          categories={categories}
          onSelect={(name) => {
            filters.setCategory(name);
          }}
        />
        <Catalog
          products={filters.filtered}
          categories={categories}
          category={filters.category}
          setCategory={filters.setCategory}
          size={filters.size}
          setSize={filters.setSize}
          sizes={filters.sizes}
          query={filters.query}
          setQuery={filters.setQuery}
          onOpen={modal.open}
        />
        <About photo={aboutPhoto} />
        <Wholesale />
        <SizeGuide />
        <SeoFaq />
        <Contacts />
      </main>
      <Footer />
      {modal.product ? <ProductModal product={modal.product} onClose={modal.close} /> : null}
    </>
  );
}
