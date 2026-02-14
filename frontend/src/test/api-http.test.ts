import { describe, expect, it, vi } from 'vitest';
import { apiFetch, ApiError } from '@/api/http';
import { HealthResponseSchema } from '@/api/schemas/health';

describe('apiFetch', () => {
  it('parses valid payload', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'ok', service: 's', version: '1' }) }));
    await expect(apiFetch('/v1/health', { method: 'GET' }, HealthResponseSchema)).resolves.toEqual({ status: 'ok', service: 's', version: '1' });
  });

  it('throws ApiError on non-2xx', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        headers: { get: () => 'application/json' },
        json: async () => ({ error: { code: 'ONLY_SOURCES_VIOLATION', message: 'no', correlation_id: 'c', retryable: false, timestamp: 't' } }),
      }),
    );
    await expect(apiFetch('/v1/query', { method: 'POST' }, HealthResponseSchema)).rejects.toBeInstanceOf(ApiError);
  });



  it('parses JSON payload without content-type header', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ status: 'ok', service: 's', version: '1' }),
      }),
    );

    await expect(apiFetch('/v1/health', { method: 'GET' }, HealthResponseSchema)).resolves.toEqual({ status: 'ok', service: 's', version: '1' });
  });

  it('keeps text payload when content-type header is missing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('upstream unavailable', { status: 503 })));

    await expect(apiFetch('/v1/query', { method: 'POST' }, HealthResponseSchema)).rejects.toMatchObject({
      message: 'Request failed',
      status: 503,
      payload: 'upstream unavailable',
    });
  });

  it('returns plain text payload as ApiError payload for non-json failures', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        headers: { get: () => 'text/plain; charset=utf-8' },
        text: async () => 'upstream unavailable',
      }),
    );

    await expect(apiFetch('/v1/query', { method: 'POST' }, HealthResponseSchema)).rejects.toMatchObject({
      message: 'Request failed',
      status: 503,
      payload: 'upstream unavailable',
    });
  });
});
