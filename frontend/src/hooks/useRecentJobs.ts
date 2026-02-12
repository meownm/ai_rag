import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/api/http';
import { z } from 'zod';
import { JobStatusResponseSchema } from '@/api/schemas/jobs';
import { useTenant } from '@/providers/TenantProvider';

const JobsListSchema = z.object({ jobs: z.array(JobStatusResponseSchema) });

export function useRecentJobs(limit = 20) {
  const { tenantId } = useTenant();
  return useQuery({
    queryKey: ['jobs', tenantId, limit],
    queryFn: () => apiFetch(`/v1/jobs/recent?tenant_id=${tenantId}&limit=${limit}`, { method: 'GET' }, JobsListSchema),
    refetchInterval: 3000,
  });
}
