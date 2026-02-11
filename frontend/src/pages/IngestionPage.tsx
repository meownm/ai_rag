import { useState } from 'react';
import { useQueries } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { useIngestion } from '@/hooks/useIngestion';
import { apiFetch } from '@/api/http';
import { JobStatusResponseSchema } from '@/api/schemas/jobs';
import { JobsTable } from '@/components/ingestion/JobsTable';
import { JobDetails } from '@/components/ingestion/JobDetails';

export function IngestionPage() {
  const [jobIds, setJobIds] = useState<string[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>();
  const ingestion = useIngestion();

  const jobsQueries = useQueries({
    queries: jobIds.map((id) => ({
      queryKey: ['job', id],
      queryFn: () => apiFetch(`/v1/jobs/${id}`, { method: 'GET' }, JobStatusResponseSchema),
      refetchInterval: 3000,
    })),
  });

  const latestJobs = jobsQueries.map((query) => query.data).filter(Boolean);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <h2 className="mb-2 text-lg font-semibold">Start Ingestion Job</h2>
        <Button
          type="button"
          onClick={async () => {
            const result = await ingestion.mutateAsync(['CONFLUENCE_PAGE']);
            setJobIds((prev) => [result.job_id, ...prev]);
            setSelectedJobId(result.job_id);
          }}
        >
          Start Sync
        </Button>
      </Card>
      <JobsTable jobs={latestJobs} onSelect={setSelectedJobId} />
      <JobDetails jobId={selectedJobId} />
    </div>
  );
}
