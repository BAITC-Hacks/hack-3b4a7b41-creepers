import type { Product } from "@/types/product";
import { ProductDetails } from "@/components/ProductDetails";

interface ProductCardProps {
  product: Product;
  onAdd?: (product: Product) => void;
}

function formatPrice(price: Product["price"], currency = "₸") {
  if (price === null || price === undefined) return "Цена уточняется";
  return `${new Intl.NumberFormat("ru-RU").format(price)} ${currency}`;
}

function stockLabel(product: Product) {
  if (product.stock === 0 || product.available === false) return { text: "Нет в наличии", className: "border-[#f0d8d5] bg-[#fff5f3] text-[#b64b3f]" };
  if (typeof product.stock === "number") return { text: product.stock < 5 ? `Осталось ${product.stock} шт.` : `В наличии: ${product.stock} шт.`, className: "border-[#d7e8df] bg-[#f0f8f3] text-[var(--green)]" };
  return { text: product.availability || "Наличие уточняется", className: "border-[#e8dfca] bg-[#fffaf0] text-[#a27625]" };
}

export function ProductCard({ product, onAdd }: ProductCardProps) {
  const stock = stockLabel(product);
  const certificateUrl = product.certificateUrl || product.certificate_url;

  return (
    <article className="rounded-xl border border-[var(--line)] bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="m-0 text-sm font-bold leading-5">{product.name}</h3>
          {product.category && <p className="m-0 mt-1 text-xs text-[var(--ink-muted)]">{product.category}</p>}
        </div>
        <span className={`shrink-0 rounded-full border px-2 py-1 text-[0.65rem] font-bold ${stock.className}`}>{stock.text}</span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 rounded-lg bg-[#f7fafb] p-3 text-xs">
        <div><p className="m-0 text-[var(--ink-muted)]">Артикул</p><p className="m-0 mt-1 font-semibold">{product.article || "Не указан"}</p></div>
        <div><p className="m-0 text-[var(--ink-muted)]">Цена</p><p className="m-0 mt-1 font-semibold">{formatPrice(product.price, product.currency || "₸")}</p></div>
      </div>
      {product.description && <p className="mb-0 mt-3 text-xs leading-5 text-[var(--ink-muted)]">{product.description}</p>}
      <ProductDetails product={product} />
      <div className="mt-4 flex items-center justify-between gap-3">
        {certificateUrl ? <a href={certificateUrl} target="_blank" rel="noreferrer" className="text-xs font-bold text-[var(--blue)] underline-offset-2 hover:underline">Открыть сертификат</a> : <span className="text-xs text-[var(--ink-muted)]">Сертификат недоступен</span>}
        {onAdd && product.available !== false && product.stock !== 0 && <button type="button" onClick={() => onAdd(product)} className="rounded-lg bg-[var(--blue)] px-3 py-2 text-xs font-bold text-white transition hover:bg-[var(--blue-dark)] focus:outline-none focus:ring-2 focus:ring-[var(--blue)] focus:ring-offset-2">Добавить</button>}
      </div>
    </article>
  );
}