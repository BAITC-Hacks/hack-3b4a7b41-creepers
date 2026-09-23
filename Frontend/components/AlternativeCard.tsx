import type { AlternativeProduct } from "@/types/product";
import { ProductCard } from "@/components/ProductCard";

interface AlternativeCardProps {
  alternative: AlternativeProduct;
  onAdd?: (product: AlternativeProduct) => void;
}

export function AlternativeCard({ alternative, onAdd }: AlternativeCardProps) {
  return <div className="rounded-xl border border-[#d8e6f0] bg-[#f5faff] p-3"><p className="m-0 mb-2 text-xs font-bold uppercase tracking-[0.08em] text-[var(--blue)]">Возможная альтернатива</p><ProductCard product={alternative} onAdd={onAdd} />{alternative.reason && <p className="m-0 mt-2 text-xs leading-5 text-[var(--ink-muted)]"><strong className="text-[var(--foreground)]">Почему подходит:</strong> {alternative.reason}</p>}</div>;
}