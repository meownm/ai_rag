import type { AssistantPayload } from '@/components/conversation/types';
import { DetailsBlock } from '@/components/conversation/DetailsBlock';
import { SourcesBlock } from '@/components/conversation/SourcesBlock';
import { SummaryBlock } from '@/components/conversation/SummaryBlock';

export function AssistantMessage({ payload, showDebug, onSourceClick }: { payload: AssistantPayload; showDebug: boolean; onSourceClick: (idx: number) => void }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <SummaryBlock summary={payload.summary} />
      <DetailsBlock details={payload.details} />
      <SourcesBlock sources={payload.sources} onSourceClick={onSourceClick} />
      {showDebug && payload.debug ? (
        <div className="mt-3 rounded-md bg-slate-100 p-2 text-xs text-slate-600" aria-label="Debug transparency panel">
          <div>Interpreted query: {payload.debug.interpretedQuery ?? '-'}</div>
          <div>Dynamic top_k: {payload.debug.dynamicTopK ?? '-'}</div>
          <div>Chunks used: {payload.debug.chunksUsed ?? '-'}</div>
          <div>Coverage ratio: {payload.debug.coverageRatio ?? '-'}</div>
          <div>Model context window: {payload.debug.modelContextWindow ?? '-'}</div>
          <div>Confidence: {payload.debug.confidence ?? '-'}</div>
          <div className="mt-2 font-semibold">Agent trace</div>
          <ul className="list-disc pl-4">
            {(payload.debug.agentTrace ?? []).map((stage, idx) => (
              <li key={`${stage.stage}-${idx}`}>{stage.stage}: {stage.latencyMs}ms</li>
            ))}
            {(payload.debug.agentTrace ?? []).length === 0 ? <li>-</li> : null}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
