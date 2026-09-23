interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return <div className="mt-3 flex items-center justify-between gap-3 rounded-xl border border-[#f0d8d5] bg-[#fff7f6] p-3 text-xs text-[#a24238]" role="alert"><span>{message}</span>{onRetry && <button type="button" onClick={onRetry} className="shrink-0 font-bold underline underline-offset-2">Повторить</button>}</div>;
}