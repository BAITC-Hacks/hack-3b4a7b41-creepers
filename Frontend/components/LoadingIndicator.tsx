export function LoadingIndicator() {
  return (
    <div className="flex items-center gap-3 text-sm text-[var(--ink-muted)]" role="status" aria-live="polite">
      <span className="flex gap-1" aria-hidden="true">
        <i className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--blue)]" />
        <i className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--blue)] [animation-delay:150ms]" />
        <i className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--blue)] [animation-delay:300ms]" />
      </span>
      AI анализирует запрос...
    </div>
  );
}