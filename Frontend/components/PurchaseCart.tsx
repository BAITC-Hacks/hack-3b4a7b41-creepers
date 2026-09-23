"use client";
import { useEffect, useState } from "react";
import { api, money, type Cart, type Mode } from "@/lib/workspace-api";
import Icon from "./Icon";

export default function PurchaseCart({
  session,
  mode,
}: {
  session: string;
  mode: Mode;
}) {
  const [cart, setCart] = useState<Cart | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    api<Cart>(mode, `/cart/${encodeURIComponent(session)}`)
      .then((value) => {
        if (alive) setCart(value);
      })
      .catch((err) => {
        if (alive) setError(err.message);
      });
    return () => {
      alive = false;
    };
  }, [session, mode]);
  function download() {
    if (!cart) return;
    const text = [
      `EKT Copilot — список закупки (${mode === "demo" ? "СИНТЕТИЧЕСКОЕ ДЕМО" : "каталог EKT"})`,
      "Заказ не оформлен. Цены и остатки нужно подтвердить.",
      "",
      ...cart.items.map(
        (item) =>
          `${item.product.article || item.product.id} | ${item.product.name} | ${item.quantity} ед. | ${money(item.product)}`,
      ),
    ].join("\r\n");
    const url = URL.createObjectURL(
      new Blob(["\uFEFF", text], { type: "text/plain;charset=utf-8" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "ekt-purchase-list.txt";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const totals: Record<string, number> = {};
  cart?.items.forEach(({ product, quantity }) => {
    if (product.price !== null && product.currency)
      totals[product.currency] =
        (totals[product.currency] || 0) + Number(product.price) * quantity;
  });
  return (
    <div className="cart-page">
      <header>
        <a href={`/?mode=${mode}`} className="brand">
          <span className="brand-symbol">
            <Icon name="bolt" />
          </span>
          <span>
            ekt<span className="brand-dot">.</span>
            <small>PROCUREMENT COPILOT</small>
          </span>
        </a>
        <a className="secondary" href={`/?mode=${mode}`}>
          Вернуться к подбору <Icon name="arrow" size={17} />
        </a>
      </header>
      <main>
        <div className="eyebrow">
          {mode === "demo"
            ? "УЧЕБНАЯ КОРЗИНА · СИНТЕТИЧЕСКИЕ ДАННЫЕ"
            : "ВАША ЗАКУПКА · ДАННЫЕ EKT"}
        </div>
        <h1>Всё нужное — в одном списке.</h1>
        <p className="section-intro">
          Вы подтвердили эти позиции. Выгрузите список для согласования с
          менеджером.
        </p>
        <div className="notice">
          <Icon name="shield" size={18} /> Корзина прототипа. Она не создаёт
          заказ на ekt.kz и не резервирует остатки. Ссылка предоставляет доступ
          к списку — делитесь ею только с получателем закупки.
        </div>
        {error && (
          <div className="error-banner" role="alert">
            {error} Если сессия истекла или сервер перезапущен, соберите новую
            корзину.
          </div>
        )}
        {!cart && !error && <p role="status">Загружаю вашу корзину…</p>}
        {cart && (
          <>
            <div className="cart-table">
              <div className="cart-table-heading">
                <span>Товар</span>
                <span>Количество</span>
                <span>Цена за единицу</span>
              </div>
              {cart.items.map(({ product, quantity }) => (
                <div className="cart-table-row" key={product.id}>
                  <div>
                    <small>{product.article || `ID ${product.id}`}</small>
                    <h3>{product.name}</h3>
                    <small>
                      Остаток при добавлении:{" "}
                      {product.stock === null ? "нет данных" : product.stock} ·{" "}
                      {product.source === "demo_catalog"
                        ? "Учебный каталог"
                        : "Каталог EKT"}
                    </small>
                  </div>
                  <strong>{quantity} ед.</strong>
                  <span>{money(product)}</span>
                </div>
              ))}
              {!cart.items.length && (
                <div className="empty-state">
                  <Icon name="cart" size={42} />
                  <h3>Корзина пока пуста</h3>
                  <p>Найдите товар и подтвердите добавление в чате.</p>
                </div>
              )}
            </div>
            {!!cart.items.length && (
              <div className="cart-summary">
                <div>
                  <span className="muted">
                    {cart.items.length} позиций · {cart.total_items} единиц
                  </span>
                  {Object.entries(totals).map(([currency, value]) => (
                    <strong key={currency}>
                      {value.toLocaleString("ru-RU")}{" "}
                      {currency === "KZT" ? "₸" : currency}
                    </strong>
                  ))}
                  {cart.items.some(
                    (i) => !i.product.currency || i.product.price === null,
                  ) && (
                    <p className="muted">
                      Общий итог не рассчитан: для части позиций нет цены или
                      валюты.
                    </p>
                  )}
                  <small>Цены на момент добавления, без расчёта доставки</small>
                </div>
                <button className="primary" onClick={download}>
                  <Icon name="download" size={18} /> Скачать список закупки
                </button>
              </div>
            )}
          </>
        )}
        <a
          className="source-link"
          href="https://ekt.kz/about/faq/"
          target="_blank"
          rel="noreferrer"
        >
          Как связаться с менеджером EKT <Icon name="link" size={15} />
        </a>
      </main>
      <footer>Creepers · HackAlem AI 2026</footer>
    </div>
  );
}
