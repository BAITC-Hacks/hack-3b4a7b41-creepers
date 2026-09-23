interface ChatInputProps {
  value: string;
  isLoading: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
  selectedFiles: File[];
  onFilesChange: (files: File[]) => void;
}

export function ChatInput({ value, isLoading, onChange, onSend, selectedFiles, onFilesChange }: ChatInputProps) {
  return (
    <div className="border-t border-[var(--line)] bg-white p-4 max-sm:p-3">
      <div className="flex items-end gap-3 rounded-2xl border border-[var(--line)] bg-[#f8fafb] p-2 shadow-sm focus-within:border-[var(--blue)] focus-within:ring-2 focus-within:ring-[rgba(18,97,160,0.12)]">
        <label className="flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-xl border border-[var(--line)] bg-white text-lg text-[var(--ink-muted)] hover:border-[var(--blue)]" title="Прикрепить файл">
          <span aria-hidden="true">+</span>
          <span className="sr-only">Прикрепить файл</span>
          <input type="file" multiple accept=".xlsx,.xls,.docx,.doc,.pdf,.jpg,.jpeg,.png" className="hidden" onChange={(event) => onFilesChange(Array.from(event.target.files || []))} />
        </label>
        <label className="sr-only" htmlFor="chat-message">Ваш вопрос</label>
        <textarea id="chat-message" value={value} onChange={(event) => onChange(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); onSend(); } }} placeholder="Напишите вопрос о товаре..." rows={1} disabled={isLoading} className="max-h-28 min-h-10 flex-1 resize-none border-0 bg-transparent px-2 py-2.5 text-sm text-[var(--foreground)] outline-none placeholder:text-[#91a0a8] disabled:cursor-not-allowed disabled:opacity-60" />
        <button type="button" onClick={onSend} disabled={isLoading || !value.trim()} className="flex h-10 shrink-0 items-center gap-2 rounded-xl bg-[var(--blue)] px-4 text-sm font-bold text-white transition hover:bg-[var(--blue-dark)] focus:outline-none focus:ring-2 focus:ring-[var(--blue)] focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-[#c8d4db]">Отправить <span aria-hidden="true">↑</span></button>
      </div>
      {selectedFiles.length > 0 && <div className="mt-2 flex flex-wrap gap-2 px-2">{selectedFiles.map((file) => <span key={`${file.name}-${file.size}`} className="rounded-md bg-[var(--blue-soft)] px-2 py-1 text-[0.68rem] text-[var(--blue)]">{file.name}</span>)}</div>}
        {selectedFiles.length > 0 && <div className="mt-2 flex flex-wrap gap-2 px-2">{selectedFiles.map((file, index) => <span key={`${file.name}-${file.size}`} className="inline-flex items-center gap-1 rounded-md bg-[var(--blue-soft)] px-2 py-1 text-[0.68rem] text-[var(--blue)]">{file.name}<button type="button" onClick={() => onFilesChange(selectedFiles.filter((_, fileIndex) => fileIndex !== index))} className="font-bold hover:text-[var(--blue-dark)]" aria-label={`Удалить файл ${file.name}`}>×</button></span>)}</div>}
      <p className="m-0 px-2 pt-2 text-[0.68rem] text-[var(--ink-muted)]">Enter — отправить · Shift + Enter — новая строка</p>
    </div>
  );
}