import type { ChatMessageData } from "@/types/chat";

interface ChatMessageProps {
  message: ChatMessageData;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const time = message.createdAt.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <article className="max-w-[min(78%,620px)] max-sm:max-w-[90%]">
        <div className={`mb-1 flex items-center gap-2 text-[0.68rem] font-semibold uppercase tracking-[0.08em] ${isUser ? "justify-end text-[var(--blue)]" : "text-[var(--ink-muted)]"}`}>
          <span>{isUser ? "Вы" : "AI-консультант"}</span>
          <time className="font-normal normal-case tracking-normal opacity-70" dateTime={message.createdAt.toISOString()}>{time}</time>
        </div>
        <div className={`rounded-2xl px-4 py-3 text-[0.94rem] leading-6 shadow-sm ${isUser ? "rounded-br-sm bg-[var(--blue)] text-white" : "rounded-bl-sm border border-[var(--line)] bg-white text-[var(--foreground)]"}`}>
          {message.content}
        </div>
      </article>
    </div>
  );
}