import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import type { JobStatusResponse } from '@/api/schemas/jobs';

export function JobsTable({ jobs, onSelect }: { jobs: JobStatusResponse[]; onSelect: (jobId: string) => void }) {
  return (
    <Card>
      <h2 className="mb-2 text-lg font-semibold">Jobs</h2>
      <div className="space-y-2 text-sm">
        {jobs.map((job) => (
          <button key={job.job_id} type="button" className="flex w-full justify-between rounded border p-2" onClick={() => onSelect(job.job_id)}>
            <span>{job.job_id}</span>
            <div className="flex items-center gap-2">
              <span>{job.result?.chunks ?? 0} chunks</span>
              <Badge value={job.job_status} />
            </div>
          </button>
        ))}
      </div>
    </Card>
  );
}
