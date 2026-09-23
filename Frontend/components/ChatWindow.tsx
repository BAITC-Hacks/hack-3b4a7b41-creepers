"use client";

import { useEffect, useRef, useState } from "react";
import { ChatInput } from "@/components/ChatInput";
import { ChatMessage } from "@/components/ChatMessage";
import { LoadingIndicator } from "@/components/LoadingIndicator";
import { WelcomeScreen } from "@/components/WelcomeScreen";
import type { ChatMessageData } from "@/types/chat";

const initialMessage: ChatMessageData = {
  id: "welcome",
  role: "assistant",
  content: "Здравствуйте! Я помогу найти товар, проверить наличие, характеристики и подобрать аналог.",
  createdAt: new Date(),
};

function createMessage(role: ChatMessageData["role"], content: string): ChatMessageData {
  return { id: crypto.randomUUID(), role, content, createdAt: new Date() };
}

function demoReply(message: string): string {
  const normalized = message.toLowerCase();
  if (normalized.includes("достав") || normalized.includes("оплат")) return "Уточню условия оплаты и доставки по вашему запросу. Подключение к каталогу и бизнес-условиям появится после интеграции с backend.";
  if (normalized.includes("аналог") || normalized.includes("отсутств")) return "Проверю наличие исходного товара и подберу альтернативу по категории и основным характеристикам.";
  return "Запрос принят. Я подключусь к каталогу Электрокомплекта и верну точные данные о товаре, цене и наличии.";
}

export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  function sendMessage(content = input) {
    const trimmed = content.trim();
    if (!trimmed || isLoading) return;
    setMessages((current) => [...current, createMessage("user", trimmed)]);
    setInput("");
    setIsLoading(true);
    window.setTimeout(() => {
      setMessages((current) => [...current, createMessage("assistant", demoReply(trimmed))]);
      setIsLoading(false);
    }, 650);
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white shadow-[0_18px_50px_rgba(39,62,77,0.09)]">
      <div className="flex items-center justify-between border-b border-[var(--line)] px-5 py-4 max-sm:px-4">
        <div><p className="m-0 text-sm font-bold">Чат с консультантом</p><p className="m-0 mt-0.5 text-xs text-[var(--ink-muted)]">Поможем с выбором электротехнической продукции</p></div>
        <span className="rounded-md bg-[#f3f7f9] px-2 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.08em] text-[var(--ink-muted)]">Демо</span>
      </div>
      <div className="flex min-h-[560px] flex-col">
        <div className="flex-1 overflow-y-auto px-6 max-sm:px-4">
          {messages.length === 0 ? <WelcomeScreen onPrompt={sendMessage} /> : <div className="flex flex-col gap-5 py-6"><ChatMessage message={initialMessage} />{messages.map((message) => <ChatMessage key={message.id} message={message} />)}{isLoading && <LoadingIndicator />}<div ref={messagesEndRef} /></div>}
        </div>
        <ChatInput value={input} isLoading={isLoading} onChange={setInput} onSend={() => sendMessage()} />
      </div>
    </section>
  );
}