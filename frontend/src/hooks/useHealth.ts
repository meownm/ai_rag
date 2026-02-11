import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/api/http';
import { HealthResponseSchema } from '@/api/schemas/health';
import { logEvent } from '@/lib/logger';

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const result = await apiFetch('/v1/health', { method: 'GET' }, HealthResponseSchema);
      logEvent('health_loaded', { service: result.service, version: result.version });
      return result;
    },
    refetchInterval: 30_000,
  });
}
