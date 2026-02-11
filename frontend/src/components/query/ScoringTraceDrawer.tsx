import type { QueryResponse } from '@/api/schemas/query';
import { Card } from '@/components/ui/Card';

export function ScoringTraceDrawer({ citations }: { citations: QueryResponse['citations'] }) {
  return (
    <Card>
      <h2 className="mb-2 text-lg font-semibold">Scoring Trace</h2>
      <div className="space-y-2 text-sm">
        {citations.map((citation) => (
          <div key={citation.chunk_id} className="rounded border p-2">
            <p>{citation.chunk_id}</p>
            <pre className="overflow-auto text-xs">
              {JSON.stringify(citation.score_breakdown ?? { lex_score: 0, vec_score: 0, rerank_score: 0, boosts: {}, final_score: 0 }, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </Card>
  );
}
