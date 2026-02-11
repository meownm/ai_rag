import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/api/http';
import { JobStatusResponseSchema } from '@/api/schemas/jobs';
import { logEvent } from '@/lib/logger';

export function useJobStatus(jobId?: string) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: async () => {
      const result = await apiFetch(`/v1/jobs/${jobId}`, { method: 'GET' }, JobStatusResponseSchema);
      logEvent('ingestion_status', { jobId, status: result.job_status });
      return result;
    },
    enabled: Boolean(jobId),
    refetchInterval: (query) => (query.state.data?.job_status === 'done' || query.state.data?.job_status === 'error' ? false : 3000),
  });
}
