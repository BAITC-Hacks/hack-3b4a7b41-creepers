import type { PendingConfirmation } from "@/types/cart";

interface ConfirmationCardProps {
  confirmation: PendingConfirmation;
  isLoading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmationCard({ confirmation, isLoading, onConfirm, onCancel }: ConfirmationCardProps) {
  const productName = confirmation.product?.name || "Выбранный товар";
  const available = confirmation.available_stock ?? confirmation.available;
  return <section className="mt-3 rounded-xl border border-[#c9ddea] bg-[#f5faff] p-4" aria-label="Подтверждение добавления в корзину"><p className="m-0 text-sm font-bold">Подтвердите добавление</p><dl className="mt-3 grid gap-2 text-xs"><div className="flex justify-between gap-3"><dt className="text-[var(--ink-muted)]">Товар</dt><dd className="m-0 text-right font-semibold">{productName}</dd></div>{confirmation.article && <div className="flex justify-between gap-3"><dt className="text-[var(--ink-muted)]">Артикул</dt><dd className="m-0 font-semibold">{confirmation.article}</dd></div>}<div className="flex justify-between gap-3"><dt className="text-[var(--ink-muted)]">Количество</dt><dd className="m-0 font-semibold">{confirmation.quantity} шт.</dd></div>{available !== null && available !== undefined && <div className="flex justify-between gap-3"><dt className="text-[var(--ink-muted)]">Доступно</dt><dd className="m-0 font-semibold">{available} шт.</dd></div>}</dl><div className="mt-4 flex gap-2"><button type="button" disabled={isLoading} onClick={onConfirm} className="rounded-lg bg-[var(--blue)] px-3 py-2 text-xs font-bold text-white hover:bg-[var(--blue-dark)] disabled:cursor-not-allowed disabled:opacity-50">{isLoading ? "Проверяем..." : "Подтвердить"}</button><button type="button" disabled={isLoading} onClick={onCancel} className="rounded-lg border border-[var(--line)] bg-white px-3 py-2 text-xs font-bold text-[var(--foreground)] hover:border-[var(--blue)] disabled:opacity-50">Отмена</button></div></section>;
}