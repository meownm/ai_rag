import type { Citation } from '@/api/schemas/query';

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function highlightSnippet(snippet: string, term: string | null): Array<{ text: string; highlighted: boolean }> {
  if (!term || term.trim().length < 2) {
    return [{ text: snippet, highlighted: false }];
  }

  const candidate = term
    .trim()
    .split(/\s+/)
    .map((part) => part.trim())
    .find((part) => part.length >= 2 && snippet.toLowerCase().includes(part.toLowerCase()));

  if (!candidate) {
    return [{ text: snippet, highlighted: false }];
  }

  const regex = new RegExp(`(${escapeRegExp(candidate)})`, 'ig');
  return snippet
    .split(regex)
    .filter(Boolean)
    .map((part) => ({ text: part, highlighted: part.toLowerCase() === candidate.toLowerCase() }));
}

export function ChunkPreviewModal({ citation, onClose, highlightTerm }: { citation: Citation | null; onClose: () => void; highlightTerm?: string | null }) {
  if (!citation) {
    return null;
  }
  const parts = highlightSnippet(citation.snippet, highlightTerm ?? null);
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/30">
      <div className="w-full max-w-2xl rounded-lg bg-white p-4 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">{citation.title}</h3>
          <button className="text-sm text-slate-500 hover:underline" onClick={onClose}>
            Закрыть
          </button>
        </div>
        <p className="mt-3 whitespace-pre-wrap rounded bg-yellow-50 p-3 text-sm">
          {parts.map((part, idx) =>
            part.highlighted ? (
              <mark key={idx} className="rounded bg-amber-300 px-0.5">
                {part.text}
              </mark>
            ) : (
              <span key={idx}>{part.text}</span>
            ),
          )}
        </p>
      </div>
    </div>
  );
}
