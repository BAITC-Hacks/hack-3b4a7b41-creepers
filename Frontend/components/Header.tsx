export function Header() {
  return (
    <header className="border-b border-[var(--line)] bg-white/85 backdrop-blur-sm">
      <div className="mx-auto flex w-[min(1180px,calc(100%-40px))] items-center justify-between py-5 max-sm:w-[min(100%-24px,1180px)]">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--blue)] text-lg font-bold text-white shadow-[0_8px_18px_rgba(18,97,160,0.2)]" aria-hidden="true">
            Э
          </div>
          <div>
            <p className="m-0 text-[0.98rem] font-bold tracking-[-0.01em]">Электрокомплект</p>
            <p className="m-0 text-[0.74rem] text-[var(--ink-muted)]">AI-консультант по электротехнической продукции</p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-[#d7e8df] bg-[#f0f8f3] px-3 py-1.5 text-xs font-semibold text-[var(--green)]">
          <span className="h-2 w-2 rounded-full bg-[var(--green)] shadow-[0_0_0_3px_rgba(47,139,99,0.12)]" aria-hidden="true" />
          Онлайн
        </div>
      </div>
    </header>
  );
}