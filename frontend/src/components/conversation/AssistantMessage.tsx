import type { AssistantPayload } from './types';

export function AssistantMessage({ payload, showDebug, onSourceClick }: { payload: AssistantPayload; showDebug: boolean; onSourceClick: (idx: number) => void }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">Summary</div>
      <div className="mt-1 font-medium text-slate-900">{payload.summary}</div>
      <div className="mt-3 text-xs uppercase tracking-wide text-slate-500">Details</div>
      <div className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{payload.details}</div>
      <div className="mt-3 text-xs uppercase tracking-wide text-slate-500">Sources</div>
      <ul className="mt-1 space-y-1 text-sm">
        {payload.sources.map((source, index) => (
          <li key={source.chunk_id}>
            <button className="text-left text-indigo-600 hover:underline" onClick={() => onSourceClick(index)}>
              {source.title}
            </button>
          </li>
        ))}
      </ul>
      {showDebug && payload.debug ? (
        <div className="mt-3 rounded-md bg-slate-100 p-2 text-xs text-slate-600">
          <div>Interpreted query: {payload.debug.interpretedQuery ?? '-'}</div>
          <div>Dynamic top_k: {payload.debug.dynamicTopK ?? '-'}</div>
          <div>Chunks used: {payload.debug.chunksUsed ?? '-'}</div>
          <div>Coverage ratio: {payload.debug.coverageRatio ?? '-'}</div>
          <div>Model context window: {payload.debug.modelContextWindow ?? '-'}</div>
          <div>Confidence: {payload.debug.confidence ?? '-'}</div>
        </div>
      ) : null}
    </div>
  );
}
