import { Card } from '@/components/ui/Card';

export function LatestErrorsCard() {
  return (
    <Card>
      <h2 className="mb-2 text-lg font-semibold">Latest Errors</h2>
      <p className="text-sm text-slate-500">No logs endpoint in current OpenAPI. Panel reserved.</p>
    </Card>
  );
}
