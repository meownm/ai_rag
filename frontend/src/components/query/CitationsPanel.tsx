import { Card } from '@/components/ui/Card';
import type { QueryResponse } from '@/api/schemas/query';

export function CitationsPanel({ citations }: { citations: QueryResponse['citations'] }) {
  return (
    <Card>
      <h2 className="mb-2 text-lg font-semibold">Citations</h2>
      <ul className="space-y-2 text-sm">
        {citations.map((citation) => (
          <li key={citation.chunk_id} className="rounded border p-2">
            <p className="font-medium">{citation.title}</p>
            <p>chunk_id: {citation.chunk_id}</p>
            <p>source_url: {citation.url}</p>
            {citation.file_path ? <p>file_path: {citation.file_path}</p> : null}
            {citation.headings_path?.length ? <p>headings_path: {citation.headings_path.join(' > ')}</p> : null}
          </li>
        ))}
      </ul>
    </Card>
  );
}
