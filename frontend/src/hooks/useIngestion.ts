import { useMutation } from '@tanstack/react-query';
import { apiFetch } from '@/api/http';
import { JobAcceptedResponseSchema } from '@/api/schemas/jobs';
import { useTenant } from '@/providers/TenantProvider';
import { logEvent } from '@/lib/logger';

export function useIngestion() {
  const { tenantId } = useTenant();

  return useMutation({
    mutationFn: async (source_types: string[]) => {
      const response = await apiFetch(
        '/v1/ingest/sources/sync',
        {
          method: 'POST',
          body: JSON.stringify({ tenant_id: tenantId, source_types }),
        },
        JobAcceptedResponseSchema,
      );
      logEvent('ingestion_started', { tenantId, jobId: response.job_id });
      return response;
    },
  });
}
