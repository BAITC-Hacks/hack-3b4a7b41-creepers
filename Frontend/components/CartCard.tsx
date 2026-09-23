import type { Cart } from "@/types/cart";

interface CartCardProps {
  cart: Cart;
  checkoutUrl?: string | null;
}

export function CartCard({ cart, checkoutUrl }: CartCardProps) {
  const url = checkoutUrl || cart.checkout_url;
  return <section className="mt-3 rounded-xl border border-[#cde4d7] bg-[#f3fbf6] p-4" aria-label="Корзина обновлена"><p className="m-0 text-sm font-bold text-[var(--green)]">Корзина обновлена</p><div className="mt-3 grid gap-2">{cart.items?.map((item, index) => <div key={`${item.product_id || item.name || "item"}-${index}`} className="flex items-center justify-between gap-3 border-b border-[#dcefe3] pb-2 text-xs"><span>{item.product?.name || item.name || "Товар"}</span><strong>{item.quantity} шт.</strong></div>)}</div>{cart.total !== null && cart.total !== undefined && <p className="mb-0 mt-3 text-sm font-bold">Итого: {new Intl.NumberFormat("ru-RU").format(cart.total)} {cart.currency || "₸"}</p>}{url && <a href={url} target="_blank" rel="noreferrer" className="mt-4 inline-flex rounded-lg bg-[var(--green)] px-3 py-2 text-xs font-bold text-white hover:brightness-95">Перейти к оформлению →</a>}</section>;
}