"use client";
import { useState } from "react";
import Icon from "./Icon";
import { money, safeLink, type Product } from "@/lib/workspace-api";

export default function CatalogProduct({
  product: p,
  busy,
  onPrepare,
  onDetail,
  onAlternatives,
  reason,
}: {
  product: Product;
  busy: boolean;
  onPrepare: (p: Product, quantity: number) => void;
  onDetail: (p: Product) => void;
  onAlternatives: (p: Product) => void;
  reason?: string;
}) {
  const [quantity, setQuantity] = useState(1);
  const available = p.stock !== null && Number(p.stock) > 0;
  const stockText =
    p.stock === null
      ? "Остаток уточняется"
      : available
        ? `В наличии: ${p.stock}`
        : "Нет в наличии";
  return (
    <article className="catalog-product">
      <div className="product-top">
        <div className="product-picture">
          {p.image_url &&
          safeLink(
            p.image_url,
          ) /* eslint-disable-next-line @next/next/no-img-element */ ? (
            <img
              src={safeLink(p.image_url)}
              alt={p.name}
              loading="lazy"
              referrerPolicy="no-referrer"
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
          ) : (
            <Icon name="bolt" size={38} />
          )}
        </div>
        <div className="product-heading">
          <div className="eyebrow">{p.article || `ID ${p.id}`}</div>
          <h3>{p.name}</h3>
          <span className={`stock ${available ? "available" : ""}`}>
            <i />
            {stockText}
          </span>
        </div>
      </div>
      {reason && (
        <div className="match-reason">
          <Icon name="shield" size={17} />
          <span>{reason}</span>
        </div>
      )}
      <div className="spec-chips">
        {Object.entries(p.specifications)
          .slice(0, 3)
          .map(([key, value]) => (
            <span key={key} title={key}>
              {value}
            </span>
          ))}
      </div>
      {p.data_warnings.map((warning) => (
        <p className="warning" key={warning}>
          {warning}
        </p>
      ))}
      <details>
        <summary>
          Характеристики и документы <Icon name="plus" size={14} />
        </summary>
        {p.description && <p className="description">{p.description}</p>}
        <dl>
          {Object.entries(p.specifications).map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        {!Object.keys(p.specifications).length && (
          <p className="muted">Характеристики ещё не получены.</p>
        )}
        {p.certificates.length ? (
          p.certificates.map((url) => (
            <a
              className="document-link"
              key={url}
              href={safeLink(url)}
              target="_blank"
              rel="noreferrer"
            >
              <Icon name="file" size={16} /> Сертификат / документ{" "}
              <Icon name="link" size={14} />
            </a>
          ))
        ) : (
          <p className="muted">В доступных данных сертификат отсутствует.</p>
        )}
        {p.product_url && (
          <a
            className="document-link"
            href={safeLink(p.product_url)}
            target="_blank"
            rel="noreferrer"
          >
            Открыть на ekt.kz <Icon name="link" size={14} />
          </a>
        )}
        <button
          className="text-button"
          disabled={busy}
          onClick={() => onDetail(p)}
        >
          Обновить данные товара
        </button>
      </details>
      <div className="product-footer">
        <strong>{money(p)}</strong>
        {available ? (
          <div className="product-actions">
            <input
              aria-label={`Количество ${p.name}`}
              type="number"
              min="1"
              max={Math.floor(Number(p.stock))}
              value={quantity || ""}
              onChange={(e) => setQuantity(Number(e.target.value))}
            />
            <button
              className="add-button"
              aria-label={`Добавить ${p.name}`}
              disabled={
                busy ||
                !Number.isInteger(quantity) ||
                quantity < 1 ||
                quantity > Number(p.stock)
              }
              onClick={() => onPrepare(p, quantity)}
            >
              <Icon name="plus" size={17} /> В корзину
            </button>
          </div>
        ) : (
          <button
            className="secondary small"
            disabled={busy}
            onClick={() => (p.stock === null ? onDetail(p) : onAlternatives(p))}
          >
            {p.stock === null ? "Уточнить наличие" : "Найти аналог"}
          </button>
        )}
      </div>
    </article>
  );
}
