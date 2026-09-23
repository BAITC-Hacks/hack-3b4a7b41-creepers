"use client";
import { useEffect, useRef, useState } from "react";
import Icon, { type IconName } from "./Icon";
import CatalogProduct from "./CatalogProduct";
import ProductComparison from "./ProductComparison";
import ProcurementSummary from "./ProcurementSummary";
import {
  api,
  cartLink,
  money,
  sessionFor,
  type Cart,
  type Mode,
  type Pending,
  type Product,
  type Reply,
  type Status,
  type Attachment,
  type ProcurementReport,
} from "@/lib/workspace-api";

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  products?: Product[];
  alternatives?: Reply["alternatives"];
  intent?: string;
};
type Tab = "chat" | "catalog" | "conditions";
const navigation: { id: Tab; icon: IconName; label: string }[] = [
  { id: "chat", icon: "spark", label: "AI-консультант" },
  { id: "catalog", icon: "grid", label: "Каталог товаров" },
  { id: "conditions", icon: "truck", label: "Оплата и доставка" },
];

export default function EktWorkspace({ mode }: { mode: Mode }) {
  const [session, setSession] = useState("");
  const [status, setStatus] = useState<Status | null>(null);
  const [tab, setTab] = useState<Tab>("chat");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [cart, setCart] = useState<Cart | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Product[] | null>(null);
  const [catalogPage, setCatalogPage] = useState<number | null>(null);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [searchNote, setSearchNote] = useState("");
  const [elapsed, setElapsed] = useState<number | null>(null);
  const [attachment, setAttachment] = useState<Attachment | null>(null);
  const [report, setReport] = useState<ProcurementReport | null>(null);
  const [comparison, setComparison] = useState<Product[]>([]);
  const [queue, setQueue] = useState<{ product: Product; quantity: number }[]>(
    [],
  );
  const [activity, setActivity] = useState("Проверяю данные каталога…");
  const [retry, setRetry] = useState<(() => void) | null>(null);
  const [recognizeImage, setRecognizeImage] = useState(false);
  const lock = useRef(false);
  const end = useRef<HTMLDivElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let alive = true;
    try {
      const id = sessionFor(mode);
      // Browser-only identity avoids sharing sessions across visitors or modes.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSession(id);
      api<Cart>(mode, `/cart/${id}`)
        .then((value) => {
          if (alive) setCart(value);
        })
        .catch(() => {});
    } catch {
      setError("Разрешите локальное хранилище браузера для работы корзины.");
    }
    api<Status>(mode, "/status")
      .then((value) => {
        if (alive) setStatus(value);
      })
      .catch(() => {
        if (alive)
          setError("Backend недоступен. Запустите его по инструкции в README.");
      });
    return () => {
      alive = false;
    };
  }, [mode]);
  useEffect(() => {
    if (messages.length || pending || busy)
      end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, pending, busy]);

  async function perform(
    action: () => Promise<void>,
    label = "Проверяю данные каталога…",
    allowRetry = true,
  ) {
    if (lock.current || !session) return;
    lock.current = true;
    setBusy(true);
    setError("");
    setRetry(null);
    setActivity(label);
    // Called only from user event handlers; this measures the completed request.
    // eslint-disable-next-line react-hooks/purity
    const started = performance.now();
    try {
      await action();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Не удалось выполнить запрос.",
      );
      if (allowRetry)
        setRetry(() => () => {
          void perform(action, label);
        });
    } finally {
      setElapsed((performance.now() - started) / 1000);
      lock.current = false;
      setBusy(false);
    }
  }
  function add(message: Omit<Message, "id">) {
    setMessages((previous) => [
      ...previous,
      { ...message, id: crypto.randomUUID() },
    ]);
  }
  async function send(text: string) {
    if (!text.trim() || lock.current) return;
    setTab("chat");
    setInput("");
    const label = /сравн|салыстыр/i.test(text)
      ? "Сверяю характеристики товаров…"
      : /аналог|замен/i.test(text)
        ? "Проверяю наличие и подходящие альтернативы…"
        : /excel|закупк|талда/i.test(text)
          ? "Сверяю позиции закупки с каталогом…"
          : /добав|штук|дана/i.test(text)
            ? "Проверяю остаток перед добавлением…"
            : "Ищу ответ и товары в каталоге…";
    await perform(
      async () => {
        add({ role: "user", text });
        const response = await api<Reply>(mode, "/chat", {
          session_id: session,
          message: text,
        });
        add({
          role: "assistant",
          text: response.message,
          products: response.products,
          alternatives: response.alternatives,
          intent: response.intent,
        });
        if (response.error) {
          if (
            ["add_to_cart_prepare", "add_to_cart_confirm"].includes(
              response.intent,
            )
          ) {
            setPending(null);
            setQueue([]);
          }
          throw new Error(response.error.message);
        }
        if (response.intent === "procurement_analysis") {
          try {
            setReport(
              await api<ProcurementReport>(
                mode,
                `/chat/procurement/${session}`,
              ),
            );
          } catch {
            /* The chat explains when an upload is required. */
          }
        }
        if (response.pending_confirmation) {
          setPending(response.pending_confirmation);
          setQueue([]);
        } else if (
          response.intent === "product_search" ||
          (response.error &&
            ["add_to_cart_prepare", "add_to_cart_confirm"].includes(
              response.intent,
            )) ||
          response.cart ||
          (response.products.length &&
            [
              "product_details",
              "stock_check",
              "certificate_request",
              "alternative_request",
            ].includes(response.intent) &&
            response.products[0].id !== pending?.product.id)
        ) {
          setPending(null);
          if (response.intent !== "add_to_cart_confirm") setQueue([]);
        }
        if (response.cart) setCart(response.cart);
        if (response.intent === "add_to_cart_confirm" && queue.length) {
          const [next, ...rest] = queue;
          setQueue(rest);
          setPending(
            await api<Pending>(mode, "/cart/prepare", {
              session_id: session,
              product_id: next.product.id,
              quantity: next.quantity,
            }),
          );
        } else if (
          ["cancel_cart_action", "product_search"].includes(response.intent)
        )
          setQueue([]);
      },
      label,
      !/^\s*(да|подтверждаю|yes|confirm|i confirm|иә|растаймын)(?:[\s.,!?]|$)/i.test(
        text,
      ),
    );
  }
  async function prepare(product: Product, quantity: number) {
    setTab("chat");
    setPending(null);
    await perform(
      async () =>
        setPending(
          await api<Pending>(mode, "/cart/prepare", {
            session_id: session,
            product_id: product.id,
            quantity,
          }),
        ),
      "Проверяю свежий остаток перед подготовкой…",
    );
  }
  async function confirm() {
    await perform(
      async () => {
        try {
          setCart(
            await api<Cart>(mode, "/cart/confirm", { session_id: session }),
          );
          setPending(null);
          add({
            role: "assistant",
            text: "Готово! Товар добавлен в вашу корзину прототипа. Список можно открыть и выгрузить для закупки. Заказ в EKT ещё не оформлен.",
          });
          if (queue.length) {
            const [next, ...rest] = queue;
            setQueue(rest);
            setActivity("Проверяю следующую позицию закупки…");
            setPending(
              await api<Pending>(mode, "/cart/prepare", {
                session_id: session,
                product_id: next.product.id,
                quantity: next.quantity,
              }),
            );
          }
        } catch (err) {
          setPending(null);
          setQueue([]);
          throw err;
        }
      },
      "Повторно проверяю остаток и подтверждённое количество…",
      false,
    );
  }
  async function cancel() {
    await perform(async () => {
      const result = await api<{ cart: Cart }>(mode, "/cart/cancel", {
        session_id: session,
      });
      setPending(null);
      setQueue([]);
      setCart(result.cart);
      add({
        role: "assistant",
        text: "Добавление отменено. Состав корзины сохранён.",
      });
    }, "Отменяю ожидающее добавление…");
  }
  async function search(value = query) {
    if (!value.trim()) return;
    setQuery(value);
    await perform(async () => {
      const result = await api<{
        products: Product[];
        partial: boolean;
        message: string | null;
      }>(mode, `/products/search?q=${encodeURIComponent(value)}`);
      setResults(result.products);
      setCatalogPage(null);
      setSearchNote(
        result.partial
          ? result.message ||
              "Поиск выполнен по доступной части каталога. Для точной проверки укажите ID товара."
          : "",
      );
    }, "Ищу товары в каталоге и проверяю наличие…");
  }
  async function browse(page = 1) {
    await perform(async () => {
      const result = await api<{
        products: Product[];
        page: number;
        has_next: boolean | null;
      }>(mode, `/products?page=${page}`);
      setResults(result.products);
      setCatalogPage(result.page);
      setHasNextPage(
        result.has_next !== false && result.products.length > 0 && page < 50,
      );
      setQuery("");
      setSearchNote(
        mode === "demo"
          ? "24 учебных товара. Цены и остатки синтетические: для демонстрации, не для заказа у EKT."
          : "Товары из EKT. Для точного наличия откройте карточку: список API не содержит остатков. Доступен просмотр первых 50 страниц.",
      );
    }, "Загружаю страницу каталога…");
  }
  async function upload(file: File) {
    await perform(
      async () => {
        if (file.size > 10 * 1024 * 1024)
          throw new Error("Максимальный размер файла — 10 МБ.");
        const data = new FormData();
        data.set("session_id", session);
        data.set("file", file);
        data.set("recognize_image", String(recognizeImage));
        const result = await api<Attachment>(mode, "/chat/attachments", data);
        setAttachment(result);
        setTab("chat");
        if (result.procurement) setReport(result.procurement);
        add({
          role: "assistant",
          text: `${result.filename}: ${result.message}`,
          products: result.candidates,
          intent: result.procurement
            ? "procurement_analysis"
            : "photo_identification",
        });
      },
      /\.(jpg|jpeg|png)$/i.test(file.name)
        ? "Обрабатываю фото и проверяю кандидатов каталога…"
        : "Читаю спецификацию, проверяю остатки и возможные замены…",
    );
  }
  async function selectProcurement(index: number, productId: string) {
    await perform(
      async () =>
        setReport(
          await api<ProcurementReport>(mode, "/chat/procurement/select", {
            session_id: session,
            row_index: index,
            product_id: productId,
          }),
        ),
      "Проверяю выбранный товар и пересчитываю закупку…",
    );
  }
  async function prepareProcurement(
    items: { product: Product; quantity: number }[],
  ) {
    if (!items.length || busy) return;
    setQueue(items.slice(1));
    await prepare(items[0].product, items[0].quantity);
  }
  const productActions = {
    busy,
    onPrepare: (p: Product, quantity: number) => {
      setQueue([]);
      void prepare(p, quantity);
    },
    onDetail: (p: Product) => {
      void send(`товар ${p.id}`);
    },
    onAlternatives: (p: Product) => {
      void send(`аналоги товара ${p.id}`);
    },
    onCertificate: (p: Product) => {
      void send(`Сертификат товара ${p.id}`);
    },
    onCompare: (p: Product) =>
      setComparison((previous) =>
        previous.some((item) => item.id === p.id)
          ? previous.filter((item) => item.id !== p.id)
          : [...previous.slice(-1), p],
      ),
  };
  const demo = mode === "demo";
  const suggestions = [
    {
      icon: "search" as const,
      title: "Подобрать автомат",
      text: "Мне нужен автомат Schneider на 25А",
      hint: "Поиск по параметрам",
    },
    {
      icon: "box" as const,
      title: "Проверить наличие",
      text: `товар ${demo ? "900001" : "515282"}`,
      hint: "Характеристики и документы",
    },
    {
      icon: "spark" as const,
      title: "Найти замену",
      text: `аналоги товара ${demo ? "900003" : "33704"}`,
      hint: "Если товара нет в наличии",
    },
    {
      icon: "truck" as const,
      title: "Условия доставки",
      text: "Какие условия доставки?",
      hint: "Оплата, доставка, самовывоз",
    },
  ];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a href={`/?mode=${mode}`} className="brand">
          <span className="brand-symbol">
            <Icon name="bolt" size={24} />
          </span>
          <span>
            ekt<span className="brand-dot">.</span>
            <small>PROCUREMENT COPILOT</small>
          </span>
        </a>
        <div className="workspace-label">
          Рабочее пространство <span>01</span>
        </div>
        <nav aria-label="Главная навигация">
          {navigation.map((item) => (
            <button
              key={item.id}
              className={tab === item.id ? "nav-item active" : "nav-item"}
              onClick={() => {
                setTab(item.id);
                if (item.id === "catalog" && results === null) void browse();
              }}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.id === "chat" && <span className="nav-ai">AI</span>}
            </button>
          ))}
          <a
            className="nav-item"
            href={session ? cartLink(session, mode) : "#"}
          >
            <Icon name="cart" />
            <span>Моя корзина</span>
            <span className="nav-count">{cart?.total_items || 0}</span>
          </a>
        </nav>
        <div className="sidebar-note">
          <span className="tiny-label">МЕНЬШЕ РУТИНЫ</span>
          <h3>
            От запроса
            <br />к готовой закупке.
          </h3>
          <p>Наличие, характеристики и подбор — в одном окне.</p>
          <div className="note-line">
            <Icon name="check" size={15} /> Решение остаётся за вами
          </div>
        </div>
        <div className="sidebar-bottom">
          <span className="team-avatar">C</span>
          <div>
            <strong>Creepers</strong>
            <small>HackAlem AI · 2026</small>
          </div>
          <span className="beta">MVP</span>
        </div>
      </aside>
      <div className="workspace-body">
        <header className="topbar">
          <div className="breadcrumb">
            Рабочее пространство <span>/</span>{" "}
            <strong>{navigation.find((n) => n.id === tab)?.label}</strong>
          </div>
          <div className="topbar-actions">
            <span className={`connection ${status ? "connected" : ""}`}>
              <i />
              {status
                ? demo
                  ? "Учебный каталог"
                  : "Каталог EKT"
                : "Подключение…"}
            </span>
            <span className="user-avatar">Г</span>
            <span
              className="ai-mode-badge"
              title={
                status?.language_model_configured
                  ? "Ключ модели настроен на сервере"
                  : "Детерминированные сценарии без AI-ключа"
              }
            >
              {status?.language_model_configured ? "AI MODE" : "DEMO MODE"}
            </span>
          </div>
        </header>
        <div className={`mode-banner ${demo ? "is-demo" : ""}`}>
          <span>
            <Icon name={demo ? "box" : "shield"} size={16} />
            {demo
              ? "Демо для жюри · синтетические товары, без ключей и регистрации"
              : "Реальный каталог EKT · корзина работает внутри прототипа"}
          </span>
          <a href={`/?mode=${demo ? "live" : "demo"}`}>
            {demo ? "Открыть реальный каталог" : "Попробовать демо"}
            <Icon name="arrow" size={14} />
          </a>
        </div>
        <div className="content-grid">
          <main className="main-panel">
            <div className="page-heading">
              <div>
                <div className="eyebrow">ВАШ ПОМОЩНИК В ЗАКУПКАХ</div>
                <h1>
                  {tab === "chat"
                    ? "AI-консультант"
                    : tab === "catalog"
                      ? "Каталог товаров"
                      : "Всё о покупке"}
                </h1>
              </div>
              <span className="heading-icon">
                <Icon
                  name={
                    tab === "chat"
                      ? "spark"
                      : tab === "catalog"
                        ? "grid"
                        : "truck"
                  }
                  size={25}
                />
              </span>
            </div>
            {error && (
              <div role="alert" className="error-banner">
                <span>{error}</span>
                {retry && (
                  <button
                    className="secondary small"
                    disabled={busy}
                    onClick={retry}
                  >
                    Повторить
                  </button>
                )}
                <button
                  aria-label="Закрыть ошибку"
                  onClick={() => setError("")}
                >
                  <Icon name="close" size={17} />
                </button>
              </div>
            )}
            {tab === "chat" && (
              <>
                <div
                  className="demo-quick-actions"
                  aria-label="Быстрые сценарии"
                >
                  {[
                    [
                      "🔎 Найти автомат 25А",
                      "Мне нужен автомат Schneider на 25А",
                    ],
                    ["📦 Проверить наличие", "Есть ли в наличии?"],
                    [
                      "🔄 Найти аналог",
                      demo ? "Есть аналог товара 900003?" : "Есть аналог?",
                    ],
                    [
                      "📊 Сравнить товары",
                      comparison.length === 2
                        ? `Сравни товары ${comparison.map((p) => p.id).join(" и ")}`
                        : demo
                          ? "Сравни товары 900001 и 900002"
                          : "Сравни эти два товара",
                    ],
                    ["📄 Анализ закупки", "Проанализируй мой Excel"],
                    ["📷 Товар по фото", "Что это за товар по фото?"],
                    ["🛒 Подготовить закупку", "Подготовить закупку"],
                  ].map(([title, text]) => (
                    <button
                      key={title}
                      disabled={busy || !session}
                      onClick={() => send(text)}
                    >
                      {title}
                    </button>
                  ))}
                </div>
                {!!comparison.length && (
                  <div className="comparison-selection">
                    <span>
                      Сравнить:{" "}
                      {comparison.map((p) => p.article || p.id).join(" + ")} (
                      {comparison.length}/2)
                    </span>
                    <button
                      disabled={comparison.length !== 2 || busy}
                      onClick={() =>
                        send(
                          `Сравни товары ${comparison.map((p) => p.id).join(" и ")}`,
                        )
                      }
                    >
                      Показать таблицу
                    </button>
                    <button
                      onClick={() => setComparison([])}
                      aria-label="Очистить сравнение"
                    >
                      <Icon name="close" size={14} />
                    </button>
                  </div>
                )}
                <section
                  className="conversation"
                  aria-label="Диалог с консультантом"
                >
                  {!messages.length && !pending && (
                    <div className="welcome">
                      <div className="welcome-graphic">
                        <div className="orbit orbit-one" />
                        <div className="orbit orbit-two" />
                        <span className="floating-chip chip-left">
                          <Icon name="shield" size={16} /> Проверка наличия
                        </span>
                        <div className="spark-tile">
                          <Icon name="spark" size={44} />
                        </div>
                        <span className="floating-chip chip-right">
                          <Icon name="box" size={16} /> Подбор товаров
                        </span>
                      </div>
                      <div className="welcome-caption">
                        ЭЛЕКТРОТЕХНИКА. БЕЗ ЛИШНИХ ПОИСКОВ.
                      </div>
                      <h2>
                        Найдём то, что нужно
                        <br />
                        <span>для вашего проекта.</span>
                      </h2>
                      <p>
                        Опишите задачу или укажите артикул.
                        <br />
                        Помогу с наличием, аналогами и подготовкой корзины.
                      </p>
                      <div className="suggestions">
                        {suggestions.map((item) => (
                          <button
                            disabled={busy || !session}
                            key={item.title}
                            onClick={() => send(item.text)}
                          >
                            <span className="suggestion-icon">
                              <Icon name={item.icon} />
                            </span>
                            <strong>{item.title}</strong>
                            <small>{item.hint}</small>
                            <Icon name="arrow" size={16} />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  <div
                    className="messages"
                    aria-live="polite"
                    aria-relevant="additions"
                  >
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`message ${message.role}`}
                      >
                        <div className="message-avatar">
                          {message.role === "assistant" ? (
                            <Icon name="spark" size={18} />
                          ) : (
                            "В"
                          )}
                        </div>
                        <div className="message-content">
                          <div className="message-author">
                            {message.role === "assistant"
                              ? "EKT Copilot"
                              : "Вы"}
                            {message.role === "assistant" && (
                              <span>КОНСУЛЬТАНТ</span>
                            )}
                          </div>
                          <p className="message-text">{message.text}</p>
                          {message.intent === "product_compare" &&
                            message.products && (
                              <ProductComparison products={message.products} />
                            )}
                          {!!message.products?.length &&
                            ![
                              "product_compare",
                              "procurement_analysis",
                            ].includes(message.intent || "") && (
                              <div className="product-grid">
                                {message.products.map((product) => (
                                  <CatalogProduct
                                    key={product.id}
                                    product={product}
                                    {...productActions}
                                  />
                                ))}
                              </div>
                            )}
                          {!!message.alternatives?.length && (
                            <>
                              <h3 className="alternatives-title">
                                <Icon name="spark" size={17} /> Подходящие
                                варианты
                              </h3>
                              <div className="product-grid">
                                {message.alternatives.map(
                                  ({ product, reason }) => (
                                    <CatalogProduct
                                      key={product.id}
                                      product={product}
                                      reason={reason}
                                      {...productActions}
                                    />
                                  ),
                                )}
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  {report && (
                    <ProcurementSummary
                      report={report}
                      busy={busy || !!pending}
                      onSelect={selectProcurement}
                      onPrepare={prepareProcurement}
                    />
                  )}
                  {pending && (
                    <section
                      className="confirmation"
                      aria-label="Подтверждение добавления"
                    >
                      <div className="confirmation-title">
                        <span className="confirm-icon">
                          <Icon name="shield" />
                        </span>
                        <div>
                          <h3>Добавить в корзину?</h3>
                          <p>
                            Состав изменится только после вашего подтверждения
                          </p>
                          {!!queue.length && (
                            <p>
                              Далее в закупке: {queue.length} позиций. Каждая
                              потребует подтверждения.
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="confirmation-item">
                        <strong>{pending.product.name}</strong>
                        <span>
                          {pending.quantity} ед.{" "}
                          <small>из {pending.available_stock} доступных</small>
                        </span>
                      </div>
                      <div className="confirmation-buttons">
                        <button
                          className="primary"
                          disabled={busy}
                          onClick={confirm}
                        >
                          <Icon name="check" size={17} /> Да, добавь{" "}
                          {pending.quantity}
                        </button>
                        <button
                          className="secondary"
                          disabled={busy}
                          onClick={cancel}
                        >
                          Отмена
                        </button>
                      </div>
                    </section>
                  )}
                  {busy && (
                    <div className="thinking" role="status">
                      <span />
                      <span />
                      <span /> {activity}
                    </div>
                  )}
                  <div ref={end} />
                </section>
                <div className="composer-area">
                  {attachment && (
                    <div className="attachment-card">
                      <Icon name="file" />
                      <div>
                        <strong>{attachment.filename}</strong>
                        <p>{attachment.message}</p>
                        {attachment.extracted_text && (
                          <details>
                            <summary>Посмотреть извлечённый текст</summary>
                            <pre>{attachment.extracted_text}</pre>
                            <div className="quick-filters">
                              {attachment.extracted_text
                                .split(/\n/)
                                .filter((line) => line.trim().length > 2)
                                .slice(0, 8)
                                .map((line, i) => (
                                  <button
                                    type="button"
                                    disabled={busy}
                                    key={i}
                                    onClick={() =>
                                      setInput(
                                        `Найди ${line.split(" | ")[0].slice(0, 150)}`,
                                      )
                                    }
                                  >
                                    {line.slice(0, 65)}
                                  </button>
                                ))}
                            </div>
                          </details>
                        )}
                      </div>
                      <button
                        aria-label="Убрать вложение"
                        onClick={() => setAttachment(null)}
                      >
                        <Icon name="close" size={16} />
                      </button>
                    </div>
                  )}
                  <form
                    className="composer"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void send(input);
                    }}
                  >
                    <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Например: нужен автомат на 25А для щита…"
                      aria-label="Сообщение консультанту"
                      maxLength={2000}
                      rows={2}
                      onKeyDown={(e) => {
                        if (
                          e.key === "Enter" &&
                          !e.shiftKey &&
                          !e.nativeEvent.isComposing
                        ) {
                          e.preventDefault();
                          void send(input);
                        }
                      }}
                    />
                    <div className="composer-toolbar">
                      <div>
                        <button
                          type="button"
                          className="attach-button"
                          disabled={busy || !session}
                          onClick={() => fileInput.current?.click()}
                          title="Загрузить спецификацию"
                        >
                          <Icon name="plus" size={18} />
                          <span>Прикрепить файл</span>
                        </button>
                        <span className="file-types">
                          XLSX · DOCX · PDF · JPEG
                        </span>
                      </div>
                      <button
                        className="send-button"
                        type="submit"
                        disabled={!input.trim() || busy || !session}
                        aria-label="Отправить сообщение"
                      >
                        <Icon name="arrow" size={20} />
                      </button>
                    </div>
                    {status?.language_model_configured && (
                      <label className="ocr-consent">
                        <input
                          type="checkbox"
                          checked={recognizeImage}
                          onChange={(e) => setRecognizeImage(e.target.checked)}
                        />{" "}
                        Распознать фото через OpenAI (фото до 4 МБ будет
                        передано сервису)
                      </label>
                    )}
                    <input
                      ref={fileInput}
                      type="file"
                      hidden
                      accept=".xlsx,.xls,.docx,.doc,.pdf,.jpg,.jpeg,.png"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) void upload(file);
                        e.target.value = "";
                      }}
                    />
                  </form>
                  <div className="composer-footnote">
                    <span>
                      <Icon name="shield" size={12} /> Добавление только с
                      вашего согласия
                    </span>
                    <span>
                      {elapsed !== null
                        ? `Последний ответ: ${elapsed.toFixed(1)} с`
                        : "Enter — отправить · Shift + Enter — перенос"}
                    </span>
                  </div>
                </div>
              </>
            )}
            {tab === "catalog" && (
              <section className="catalog-section">
                <p className="section-intro">
                  Найдите товар по названию или артикулу. Точные характеристики
                  и остатки проверяются при открытии карточки.
                </p>
                <form
                  className="catalog-search"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void search();
                  }}
                >
                  <Icon name="search" />
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Название, артикул или параметры"
                    aria-label="Поиск по каталогу"
                  />
                  <button className="primary" disabled={busy || !query.trim()}>
                    Найти
                  </button>
                </form>
                <div className="quick-filters">
                  <button disabled={busy} onClick={() => browse()}>
                    Обзор каталога
                  </button>
                  {[
                    "автомат 25А",
                    "кабель",
                    "светильник",
                    "щит",
                    "выключатель",
                  ].map((value) => (
                    <button
                      key={value}
                      disabled={busy}
                      onClick={() => search(value)}
                    >
                      {value}
                    </button>
                  ))}
                </div>
                {searchNote && <p className="notice">{searchNote}</p>}
                {busy && <p role="status">Проверяю каталог…</p>}
                {results !== null ? (
                  <>
                    <div className="results-label">
                      {catalogPage
                        ? `Страница ${catalogPage} · Товаров: ${results.length}`
                        : `Найдено: ${results.length}`}
                    </div>
                    {catalogPage !== null && (
                      <div
                        className="catalog-pagination"
                        aria-label="Страницы каталога"
                      >
                        <button
                          className="secondary"
                          disabled={busy || catalogPage <= 1}
                          onClick={() => browse(catalogPage - 1)}
                        >
                          ← Назад
                        </button>
                        <span>Страница {catalogPage}</span>
                        <button
                          className="secondary"
                          disabled={busy || !hasNextPage}
                          onClick={() => browse(catalogPage + 1)}
                        >
                          Далее →
                        </button>
                      </div>
                    )}
                    <div className="product-grid">
                      {results.map((p) => (
                        <CatalogProduct
                          key={p.id}
                          product={p}
                          {...productActions}
                        />
                      ))}
                    </div>
                    {!results.length && (
                      <div className="empty-state">
                        <Icon name="search" size={38} />
                        <h3>Пока ничего не найдено</h3>
                        <p>
                          Попробуйте короткое название или точный артикул. В
                          реальном режиме поиск ограничен доступными страницами.
                        </p>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="empty-state">
                    <Icon name="grid" size={44} />
                    <h3>Начните с того, что ищете</h3>
                    <p>
                      Например, «автомат 25А». Для проверки по ID используйте
                      чат.
                    </p>
                  </div>
                )}
              </section>
            )}
            {tab === "conditions" && (
              <section className="conditions-section">
                <p className="section-intro">
                  Условия из публичной справки EKT. Конкретную стоимость, сроки
                  и кратность подтвердит менеджер.
                </p>
                {[
                  {
                    key: "payment_info",
                    title: "Удобный способ оплаты",
                    icon: "card" as const,
                  },
                  {
                    key: "delivery_info",
                    title: "Доставка и самовывоз",
                    icon: "truck" as const,
                  },
                  {
                    key: "minimum_order",
                    title: "Минимальная партия",
                    icon: "box" as const,
                  },
                ].map((item) => (
                  <article className="policy-card" key={item.key}>
                    <span>
                      <Icon name={item.icon} size={24} />
                    </span>
                    <div>
                      <h2>{item.title}</h2>
                      <p>
                        {status?.policies[item.key] ||
                          "Загрузка проверенных условий…"}
                      </p>
                    </div>
                  </article>
                ))}
                <a
                  className="source-link"
                  href="https://ekt.kz/about/faq/"
                  target="_blank"
                  rel="noreferrer"
                >
                  Источник: официальный FAQ EKT <Icon name="link" size={14} />
                </a>
                <small className="policy-date">
                  Проверено 23 сентября 2026 · условия могут обновляться
                </small>
              </section>
            )}
          </main>
          <aside className="context-panel">
            <div className="context-heading">
              <h2>Ваша закупка</h2>
              <span className="count-pill">{cart?.items.length || 0}</span>
            </div>
            <p className="muted">Всё выбранное — под рукой</p>
            <div className="cart-preview">
              {cart?.items.length ? (
                <>
                  <div className="preview-items">
                    {cart.items.map((item) => (
                      <div key={item.product.id} className="preview-item">
                        <span className="preview-icon">
                          <Icon name="box" size={19} />
                        </span>
                        <div>
                          <strong>{item.product.name}</strong>
                          <small>
                            {item.quantity} ед. · {money(item.product)}
                          </small>
                        </div>
                        <Icon name="check" size={15} />
                      </div>
                    ))}
                  </div>
                  <a
                    className="primary full-width"
                    href={cartLink(session, mode)}
                  >
                    Открыть корзину <Icon name="arrow" size={17} />
                  </a>
                </>
              ) : (
                <div className="cart-empty">
                  <span>
                    <Icon name="cart" size={30} />
                  </span>
                  <h3>Здесь будет ваш список</h3>
                  <p>
                    Подберите товар и подтвердите добавление. Помогу с
                    остальным.
                  </p>
                </div>
              )}
            </div>
            <div className="trust-card">
              <span className="trust-icon">
                <Icon name="shield" size={22} />
              </span>
              <h3>Покупка под контролем</h3>
              <div>
                <Icon name="check" size={15} />
                <span>Остатки проверяются перед добавлением</span>
              </div>
              <div>
                <Icon name="check" size={15} />
                <span>Каждое действие — с подтверждением</span>
              </div>
              <div>
                <Icon name="check" size={15} />
                <span>Платёжные данные не нужны</span>
              </div>
            </div>
            <div className="help-card">
              <div className="tiny-label">НУЖНА ПОМОЩЬ ЧЕЛОВЕКА?</div>
              <h3>Сложная спецификация?</h3>
              <p>
                Передайте список товаров менеджеру для окончательного
                согласования.
              </p>
              <a
                href="https://ekt.kz/about/faq/"
                target="_blank"
                rel="noreferrer"
              >
                Связаться с EKT <Icon name="link" size={14} />
              </a>
            </div>
            <div className="source-status">
              <i />
              <span>
                {demo
                  ? "Учебные данные · автономное демо"
                  : "Источник товаров: EKT API"}
                <small>
                  {status?.language_model_configured
                    ? "AI-разбор подключён для сложных запросов"
                    : "Базовые сценарии работают без AI-ключа"}
                </small>
              </span>
            </div>
          </aside>
        </div>
        <footer className="mobile-footer">
          EKT Copilot · Creepers · HackAlem AI 2026
        </footer>
      </div>
    </div>
  );
}
