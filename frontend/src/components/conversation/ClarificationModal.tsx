export function ClarificationModal({ options, onSelect }: { options: string[]; onSelect: (value: string | null) => void }) {
  if (options.length === 0) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40">
      <div className="w-full max-w-md rounded-lg bg-white p-4 shadow-xl">
        <h3 className="text-lg font-semibold">Уточните вопрос</h3>
        <div className="mt-3 space-y-2">
          {options.map((option) => (
            <label key={option} className="flex cursor-pointer items-center gap-2 rounded border p-2 hover:bg-slate-50">
              <input type="radio" name="clarification" onChange={() => onSelect(option)} />
              <span>{option}</span>
            </label>
          ))}
        </div>
        <button className="mt-3 text-sm text-slate-500 hover:underline" onClick={() => onSelect(null)}>
          Отмена
        </button>
      </div>
    </div>
  );
}
