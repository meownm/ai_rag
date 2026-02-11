import { useMutation } from '@tanstack/react-query';
import { apiFetch } from '@/api/http';
import { QueryResponseSchema } from '@/api/schemas/query';
import { useTenant } from '@/providers/TenantProvider';
import { logEvent } from '@/lib/logger';

export type QueryRequestPayload = {
  query: string;
  top_k?: number;
};

export function useQueryRag() {
  const { tenantId } = useTenant();

  return useMutation({
    mutationFn: async (payload: QueryRequestPayload) => {
      logEvent('query_submitted', { tenantId, queryLength: payload.query.length });
      const result = await apiFetch(
        '/v1/query',
        {
          method: 'POST',
          body: JSON.stringify({ tenant_id: tenantId, query: payload.query, top_k: payload.top_k ?? 10 }),
        },
        QueryResponseSchema,
      );
      logEvent('query_success', { tenantId, citations: result.citations.length });
      return result;
    },
  });
}
