import { Card } from '@/components/ui/Card';
import { useHealth } from '@/hooks/useHealth';

export function HealthCard() {
  const { data, isLoading } = useHealth();
  return (
    <Card>
      <h2 className="mb-2 text-lg font-semibold">Health</h2>
      {isLoading ? <p>Loading...</p> : <pre className="rounded bg-slate-100 p-2 text-sm">{JSON.stringify(data, null, 2)}</pre>}
    </Card>
  );
}
