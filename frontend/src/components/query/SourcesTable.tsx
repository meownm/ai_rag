import type { QueryResponse } from '@/api/schemas/query';
import { Card } from '@/components/ui/Card';
import { Table } from '@/components/ui/Table';

export function SourcesTable({ citations }: { citations: QueryResponse['citations'] }) {
  return (
    <Card>
      <h2 className="mb-2 text-lg font-semibold">Sources</h2>
      <Table>
        <thead>
          <tr className="border-b">
            <th className="p-2">Chunk</th>
            <th className="p-2">Document</th>
            <th className="p-2">Snippet</th>
          </tr>
        </thead>
        <tbody>
          {citations.map((citation) => (
            <tr className="border-b" key={citation.chunk_id}>
              <td className="p-2">{citation.chunk_id}</td>
              <td className="p-2">{citation.document_id}</td>
              <td className="p-2">{citation.snippet}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}
