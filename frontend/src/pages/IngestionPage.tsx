import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { useIngestion } from '@/hooks/useIngestion';
import { JobsTable } from '@/components/ingestion/JobsTable';
import { JobDetails } from '@/components/ingestion/JobDetails';
import { useRecentJobs } from '@/hooks/useRecentJobs';

const SOURCE_TYPES = ['CONFLUENCE_PAGE', 'CONFLUENCE_ATTACHMENT', 'FILE_CATALOG_OBJECT'] as const;

export function IngestionPage() {
  const [selectedJobId, setSelectedJobId] = useState<string>();
  const [sourceTypes, setSourceTypes] = useState<string[]>(['CONFLUENCE_PAGE']);
  const ingestion = useIngestion();
  const jobsQuery = useRecentJobs(20);
  const latestJobs = jobsQuery.data?.jobs ?? [];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <h2 className="mb-2 text-lg font-semibold">Start Ingestion Job</h2>
        <div className="mb-3 space-y-2 text-sm">
          {SOURCE_TYPES.map((sourceType) => (
            <label key={sourceType} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={sourceTypes.includes(sourceType)}
                onChange={(event) => {
                  setSourceTypes((prev) =>
                    event.target.checked ? [...new Set([...prev, sourceType])] : prev.filter((item) => item !== sourceType),
                  );
                }}
              />
              {sourceType}
            </label>
          ))}
        </div>
        <Button
          type="button"
          onClick={async () => {
            const result = await ingestion.mutateAsync(sourceTypes);
            setSelectedJobId(result.job_id);
          }}
          disabled={sourceTypes.length === 0 || ingestion.isPending}
        >
          Start Sync
        </Button>
      </Card>
      <JobsTable jobs={latestJobs} onSelect={setSelectedJobId} />
      <JobDetails jobId={selectedJobId} />
    </div>
  );
}
