import { HealthCard } from '@/components/diagnostics/HealthCard';
import { LatestErrorsCard } from '@/components/diagnostics/LatestErrorsCard';
import { ManifestCard } from '@/components/diagnostics/ManifestCard';

export function DiagnosticsPage() {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <HealthCard />
      <LatestErrorsCard />
      <ManifestCard />
    </div>
  );
}
