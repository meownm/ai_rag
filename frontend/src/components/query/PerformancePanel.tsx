import { Card } from '@/components/ui/Card';

export function PerformancePanel({ timings }: { timings?: Record<string, number | undefined> }) {
  return (
    <Card>
      <h2 className="mb-2 text-lg font-semibold">Performance</h2>
      <ul className="text-sm">
        <li>t_parse_ms: {timings?.t_parse_ms ?? 'n/a'}</li>
        <li>t_lexical_ms: {timings?.t_lexical_ms ?? 'n/a'}</li>
        <li>t_vector_ms: {timings?.t_vector_ms ?? 'n/a'}</li>
        <li>t_rerank_ms: {timings?.t_rerank_ms ?? 'n/a'}</li>
        <li>t_total_ms: {timings?.t_total_ms ?? 'n/a'}</li>
      </ul>
    </Card>
  );
}
