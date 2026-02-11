import { Card } from '@/components/ui/Card';

export function ManifestCard() {
  return (
    <Card>
      <h2 className="mb-2 text-lg font-semibold">Release Manifest</h2>
      <p className="text-sm text-slate-500">No manifest endpoint in current OpenAPI. Panel reserved.</p>
    </Card>
  );
}
