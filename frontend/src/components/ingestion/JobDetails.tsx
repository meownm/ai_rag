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
          <p>started_at: {data.started_at}</p>
          <p>finished_at: {data.finished_at ?? '—'}</p>
          <p>documents: {data.result?.documents ?? 0}</p>
          <p>chunks: {data.result?.chunks ?? 0}</p>
          <p>cross_links: {data.result?.cross_links ?? 0}</p>
          <p>artifacts: {data.result?.artifacts ?? 0}</p>
          {data.error_code ? <p>error_code: {data.error_code}</p> : null}
          {data.error_message ? <pre className="overflow-auto rounded bg-slate-100 p-2">{data.error_message}</pre> : null}
        </div>
      ) : null}
    </Card>
  );
}
