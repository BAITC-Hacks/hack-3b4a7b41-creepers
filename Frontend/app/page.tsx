import { ChatWindow } from "@/components/ChatWindow";
import { Header } from "@/components/Header";

export default function Home() {
  return (
    <main className="site-shell">
      <Header />
      <section className="workspace" aria-label="Чат с AI-консультантом">
        <div className="workspace-heading">
          <div>
            <p className="eyebrow">Цифровой консультант</p>
            <h1>Подберём оборудование под вашу задачу</h1>
          </div>
          <span className="workspace-meta">Каталог и условия в одном диалоге</span>
        </div>
        <ChatWindow />
      </section>
    </main>
  );
}
