"use client";

import { useState } from "react";
import type { Product } from "@/types/product";

interface ProductDetailsProps {
  product: Product;
}

export function ProductDetails({ product }: ProductDetailsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const specifications = product.specifications ? Object.entries(product.specifications) : [];

  if (!specifications.length) return null;

  return (
    <div className="mt-3 border-t border-[var(--line)] pt-3">
      <button type="button" onClick={() => setIsOpen((open) => !open)} className="flex w-full items-center justify-between text-left text-xs font-bold text-[var(--blue)] focus:outline-none focus:ring-2 focus:ring-[var(--blue)] focus:ring-offset-2">
        Характеристики
        <span aria-hidden="true">{isOpen ? "−" : "+"}</span>
      </button>
      {isOpen && <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs max-sm:grid-cols-1">{specifications.map(([key, value]) => <div key={key} className="flex justify-between gap-3 border-b border-dashed border-[var(--line)] pb-1.5"><dt className="text-[var(--ink-muted)]">{key}</dt><dd className="m-0 text-right font-semibold">{value === null ? "Не указано" : String(value)}</dd></div>)}</dl>}
    </div>
  );
}