interface WelcomeScreenProps {
  onPrompt: (prompt: string) => void;
}

const prompts = [
  "Найди автомат на 25А",
  "Есть ли этот товар в наличии?",
  "Покажи характеристики",
  "Есть ли сертификат?",
  "Нужен аналог отсутствующего товара",
  "Каковы условия доставки?",
];

export function WelcomeScreen({ onPrompt }: WelcomeScreenProps) {
  return (
    <div className="flex min-h-[360px] flex-col justify-center py-10">
      <div className="mb-7 max-w-xl">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--blue-soft)] text-xl text-[var(--blue)]" aria-hidden="true">✦</div>
        <h2 className="mb-2 font-[Georgia] text-2xl font-medium leading-tight">Чем могу помочь?</h2>
        <p className="m-0 max-w-md text-sm leading-6 text-[var(--ink-muted)]">Спросите о продукции, наличии, характеристиках, сертификатах или условиях поставки.</p>
      </div>
      <div className="grid max-w-3xl grid-cols-2 gap-3 max-sm:grid-cols-1">
        {prompts.map((prompt) => (
          <button key={prompt} type="button" onClick={() => onPrompt(prompt)} className="group flex min-h-12 items-center justify-between rounded-xl border border-[var(--line)] bg-white px-4 py-3 text-left text-sm text-[var(--foreground)] transition hover:-translate-y-0.5 hover:border-[var(--blue)] hover:shadow-[0_8px_18px_rgba(18,97,160,0.1)] focus:outline-none focus:ring-2 focus:ring-[var(--blue)] focus:ring-offset-2">
            <span>{prompt}</span>
            <span className="ml-3 text-[var(--blue)] transition-transform group-hover:translate-x-1" aria-hidden="true">→</span>
          </button>
        ))}
      </div>
    </div>
  );
}