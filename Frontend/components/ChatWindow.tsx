"use client";

import { useEffect, useRef, useState } from "react";
import { AlternativeCard } from "@/components/AlternativeCard";
import { CartCard } from "@/components/CartCard";
import { ChatInput } from "@/components/ChatInput";
import { ChatMessage } from "@/components/ChatMessage";
import { ConfirmationCard } from "@/components/ConfirmationCard";
import { ErrorMessage } from "@/components/ErrorMessage";
import { LoadingIndicator } from "@/components/LoadingIndicator";
import { ProductList } from "@/components/ProductList";
import { WelcomeScreen } from "@/components/WelcomeScreen";
import { ApiError, confirmCart, prepareCart, sendChatMessage } from "@/lib/api";
import type { PendingConfirmation } from "@/types/cart";
import type { ChatMessageData } from "@/types/chat";
import type { AlternativeProduct, Product } from "@/types/product";

const initialMessage: ChatMessageData = {
  id: "welcome",
  role: "assistant",
  content: "Здравствуйте! Я помогу найти товар, проверить наличие, характеристики и подобрать аналог.",
  createdAt: new Date(),
};

function createMessage(role: ChatMessageData["role"], content: string, extra: Partial<ChatMessageData> = {}): ChatMessageData {
  return { id: crypto.randomUUID(), role, content, createdAt: new Date(), ...extra };
}

export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [confirmation, setConfirmation] = useState<PendingConfirmation | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState(() => {
    if (typeof window === "undefined") return "";
    const storedSessionId = window.localStorage.getItem("ekt-chat-session-id") || crypto.randomUUID();
    window.localStorage.setItem("ekt-chat-session-id", storedSessionId);
    return storedSessionId;
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function sendMessage(content = input) {
    const trimmed = content.trim();
    if (!trimmed || isLoading) return;
    setMessages((current) => [...current, createMessage("user", trimmed)]);
    setInput("");
    setError(null);
    setIsLoading(true);
    try {
      const activeSessionId = sessionId || window.localStorage.getItem("ekt-chat-session-id") || crypto.randomUUID();
      if (!sessionId) {
        window.localStorage.setItem("ekt-chat-session-id", activeSessionId);
        setSessionId(activeSessionId);
      }
      const response = await sendChatMessage(activeSessionId, trimmed);
      if (response.error) throw new ApiError(response.error);
      setMessages((current) => [...current, createMessage("assistant", response.message || "Ответ получен.", {
        products: response.products,
        alternatives: response.alternatives,
        pendingConfirmation: response.pending_confirmation,
        cart: response.cart,
        checkoutUrl: response.checkout_url,
      })]);
      setConfirmation(response.pending_confirmation || null);
    } catch (requestError) {
      const message = requestError instanceof ApiError ? requestError.message : "Не удалось обработать запрос. Попробуйте ещё раз.";
      setError(message);
      setMessages((current) => [...current, createMessage("assistant", message, { isError: true })]);
    } finally {
      setIsLoading(false);
    }
  }

  async function addProduct(product: Product, quantity = 1) {
    setError(null);
    setIsLoading(true);
    try {
      const activeSessionId = sessionId || window.localStorage.getItem("ekt-chat-session-id") || crypto.randomUUID();
      const prepared = await prepareCart(activeSessionId, product.id, quantity);
      setConfirmation(prepared);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Не удалось подготовить добавление в корзину.");
    } finally {
      setIsLoading(false);
    }
  }

  async function confirmPending() {
    if (!confirmation) return;
    setIsLoading(true);
    setError(null);
    try {
      const activeSessionId = sessionId || window.localStorage.getItem("ekt-chat-session-id") || crypto.randomUUID();
      const result = await confirmCart(activeSessionId, confirmation);
      if (!result.cart) throw new ApiError(result.message || "Не удалось подтвердить добавление товара.");
      setConfirmation(null);
      setMessages((current) => [...current, createMessage("assistant", result.message || "Товар добавлен в корзину.", { cart: result.cart, checkoutUrl: result.checkout_url })]);
    } catch (requestError) {
      const message = requestError instanceof ApiError ? requestError.message : "Не удалось подтвердить добавление товара.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  function cancelPending() {
    setConfirmation(null);
    setMessages((current) => [...current, createMessage("assistant", "Добавление отменено. Товар не был добавлен в корзину.")]);
  }

  function renderExtras(message: ChatMessageData) {
    return <>
      {message.products && <ProductList products={message.products} onAdd={(product) => addProduct(product)} />}
      {message.alternatives?.map((alternative: AlternativeProduct) => <AlternativeCard key={alternative.id} alternative={alternative} onAdd={(product) => addProduct(product)} />)}
      {message.cart && <CartCard cart={message.cart} checkoutUrl={message.checkoutUrl} />}
    </>;
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white shadow-[0_18px_50px_rgba(39,62,77,0.09)]">
      <div className="flex items-center justify-between border-b border-[var(--line)] px-5 py-4 max-sm:px-4">
        <div><p className="m-0 text-sm font-bold">Чат с консультантом</p><p className="m-0 mt-0.5 text-xs text-[var(--ink-muted)]">Поможем с выбором электротехнической продукции</p></div>
        <span className="rounded-md bg-[#f3f7f9] px-2 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.08em] text-[var(--ink-muted)]">Демо</span>
      </div>
      <div className="flex min-h-[560px] flex-col">
        <div className="flex-1 overflow-y-auto px-6 max-sm:px-4">
          {messages.length === 0 ? <WelcomeScreen onPrompt={sendMessage} /> : <div className="flex flex-col gap-5 py-6"><ChatMessage message={initialMessage} />{messages.map((message) => <div key={message.id}><ChatMessage message={message} />{message.role === "assistant" && renderExtras(message)}</div>)}{isLoading && <LoadingIndicator />}<div ref={messagesEndRef} /></div>}
        </div>
        <div className="px-6 max-sm:px-4">{confirmation && <ConfirmationCard confirmation={confirmation} isLoading={isLoading} onConfirm={confirmPending} onCancel={cancelPending} />}{error && <ErrorMessage message={error} onRetry={() => setError(null)} />}</div>
        <ChatInput value={input} isLoading={isLoading} selectedFiles={selectedFiles} onFilesChange={setSelectedFiles} onChange={setInput} onSend={() => void sendMessage()} />
      </div>
    </section>
  );
}