import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { useJobStatus } from '@/hooks/useJobStatus';

export function JobDetails({ jobId }: { jobId?: string }) {
  const { data } = useJobStatus(jobId);

  return (
    <Card>
      <h2 className="mb-2 text-lg font-semibold">Job Details</h2>
      {!jobId ? <p className="text-sm text-slate-500">Select a job.</p> : null}
      {data ? (
        <div className="space-y-2 text-sm">
          <p>job_id: {data.job_id}</p>
          <p>job_type: {data.job_type}</p>
          <p>
            status: <Badge value={data.job_status} />
          </p>
          {data.error ? <pre className="overflow-auto rounded bg-slate-100 p-2">{JSON.stringify(data.error, null, 2)}</pre> : null}
        </div>
      ) : null}
    </Card>
  );
}
