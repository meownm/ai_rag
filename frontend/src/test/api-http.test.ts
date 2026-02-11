import { describe, expect, it, vi } from 'vitest';
import { apiFetch, ApiError } from '@/api/http';
import { HealthResponseSchema } from '@/api/schemas/health';

describe('apiFetch', () => {
  it('parses valid payload', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'ok', service: 's', version: '1' }) }));
    await expect(apiFetch('/v1/health', { method: 'GET' }, HealthResponseSchema)).resolves.toEqual({ status: 'ok', service: 's', version: '1' });
  });

  it('throws ApiError on non-2xx', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ error: { code: 'ONLY_SOURCES_VIOLATION', message: 'no', correlation_id: 'c', retryable: false, timestamp: 't' } }) }));
    await expect(apiFetch('/v1/query', { method: 'POST' }, HealthResponseSchema)).rejects.toBeInstanceOf(ApiError);
  });
});
