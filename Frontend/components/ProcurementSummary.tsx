"use client";
import {
  type ProcurementReport,
  type Product,
  money,
} from "@/lib/workspace-api";
import Icon from "./Icon";

export default function ProcurementSummary({
  report,
  busy,
  onSelect,
  onPrepare,
}: {
  report: ProcurementReport;
  busy: boolean;
  onSelect: (index: number, productId: string) => void;
  onPrepare: (items: { product: Product; quantity: number }[]) => void;
}) {
  const ready = report.rows.filter(
    (row) => row.product && row.available && row.available > 0,
  );
  return (
    <section className="procurement-panel">
      <div className="procurement-heading">
        <span>
          <Icon name="file" size={20} /> Анализ закупки
        </span>
        <small>
          {report.source === "demo_catalog"
            ? "DEMO · учебные данные"
            : "Источник: каталог EKT"}
        </small>
      </div>
      <div className="procurement-metrics">
        {[
          ["Позиций", report.positions],
          ["Запрошено", report.requested],
          ["Доступно", report.available],
          ["Дефицит", report.missing],
        ].map(([label, value]) => (
          <div key={label}>
            <strong>{value}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>
      <div className="procurement-rows">
        {report.rows.map((row, index) => (
          <div key={`${row.query}-${index}`} className="procurement-row">
            <div className="procurement-row-title">
              <span
                className={
                  row.status === "available" ? "row-ok" : "row-attention"
                }
              >
                {row.status === "available" ? "✓" : "!"}
              </span>
              <div>
                <strong>{row.query}</strong>
                <small>
                  {row.product
                    ? row.product.name
                    : row.note || "Требуется уточнение"}
                </small>
              </div>
              <b>
                {row.available === null ? "?" : row.available} /{" "}
                {row.requested || "?"}
              </b>
            </div>
            {row.product && (
              <div className="procurement-price">
                {money(row.product)} ·{" "}
                {row.missing
                  ? `Не хватает: ${row.missing}`
                  : row.status === "available"
                    ? "Полностью доступно"
                    : "Остаток не подтверждён"}
              </div>
            )}
            {row.candidates.length > 1 && (
              <select
                aria-label={`Выбрать товар для ${row.query}`}
                value={row.product?.id || ""}
                disabled={busy}
                onChange={(e) => onSelect(index, e.target.value)}
              >
                <option value="" disabled>
                  Выберите совпадение из каталога
                </option>
                {row.candidates.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name} · {product.article || product.id}
                  </option>
                ))}
              </select>
            )}
            {!!row.alternatives.length && (
              <div className="procurement-alternatives">
                <small>Возможная замена — проверьте совместимость:</small>
                {row.alternatives.map(({ product, reason }) => (
                  <div key={product.id}>
                    <span>{product.name}</span>
                    <p>{reason}</p>
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() => onSelect(index, product.id)}
                    >
                      Выбрать эту замену
                    </button>
                  </div>
                ))}
              </div>
            )}
            {row.note && row.product && <p className="muted">{row.note}</p>}
          </div>
        ))}
      </div>
      <p className="procurement-explanation">
        {report.complete_positions} полностью доступны ·{" "}
        {report.shortage_positions} с дефицитом · {report.unresolved_positions}{" "}
        требуют уточнения.{report.truncated && " Показаны первые 8 строк."}{" "}
        Количества приведены в единицах из файла; единицы продажи уточните по
        товару.
      </p>
      <button
        className="primary full-width"
        disabled={busy || !ready.length}
        onClick={() =>
          onPrepare(
            ready.map((row) => ({
              product: row.product!,
              quantity: row.available!,
            })),
          )
        }
      >
        <Icon name="cart" size={17} /> Подготовить доступные позиции (
        {ready.length})
      </button>
      <p className="muted">
        Будут подготовлены только доступные количества. Каждая позиция потребует
        отдельного подтверждения. {report.message}
      </p>
    </section>
  );
}
