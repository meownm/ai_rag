import { useEffect, useState } from 'react';

export function ClarificationModal({ options, onSelect }: { options: string[]; onSelect: (value: string | null) => void }) {
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    setSelected(null);
  }, [options]);

  if (options.length === 0) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40">
      <div className="w-full max-w-md rounded-lg bg-white p-4 shadow-xl">
        <h3 className="text-lg font-semibold">Уточните вопрос</h3>
        <p className="mt-1 text-sm text-slate-500">Выберите один вариант (только radio).</p>
        <div className="mt-3 space-y-2" role="radiogroup" aria-label="Clarification options">
          {options.map((option) => (
            <label key={option} className="flex cursor-pointer items-center gap-2 rounded border p-2 hover:bg-slate-50">
              <input type="radio" name="clarification" checked={selected === option} onChange={() => setSelected(option)} />
              <span>{option}</span>
            </label>
          ))}
        </div>
        <div className="mt-3 flex items-center justify-between">
          <button className="text-sm text-slate-500 hover:underline" onClick={() => onSelect(null)}>
            Отмена
          </button>
          <button type="button" className="rounded bg-indigo-600 px-3 py-1 text-sm text-white disabled:bg-indigo-300" disabled={!selected} onClick={() => onSelect(selected)}>
            Применить
          </button>
        </div>
      </div>
    </div>
  );
}
