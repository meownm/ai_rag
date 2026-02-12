import type { Citation } from '@/api/schemas/query';

export function SourcesBlock({ sources, onSourceClick }: { sources: Citation[]; onSourceClick: (idx: number) => void }) {
  return (
    <section aria-label="Sources block">
      <div className="mt-3 text-xs uppercase tracking-wide text-slate-500">Sources</div>
      <ul className="mt-1 space-y-1 text-sm">
        {sources.map((source, index) => (
          <li key={source.chunk_id}>
            <button className="text-left text-indigo-600 hover:underline" onClick={() => onSourceClick(index)}>
              {source.title}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
