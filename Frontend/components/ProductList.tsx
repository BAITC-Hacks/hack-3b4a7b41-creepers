import type { Product } from "@/types/product";
import { ProductCard } from "@/components/ProductCard";

interface ProductListProps {
  products: Product[];
  onAdd?: (product: Product) => void;
}

export function ProductList({ products, onAdd }: ProductListProps) {
  if (!products.length) return null;
  return <div className="mt-3 grid gap-3 md:grid-cols-2">{products.map((product) => <ProductCard key={product.id} product={product} onAdd={onAdd} />)}</div>;
}