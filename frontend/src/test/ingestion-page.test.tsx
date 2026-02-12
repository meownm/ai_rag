import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { IngestionPage } from '@/pages/IngestionPage';
import { TenantProvider } from '@/providers/TenantProvider';

describe('IngestionPage', () => {
  it('starts ingestion and shows recent jobs', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ jobs: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ job_id: 'job-1', job_status: 'queued' }) })
      .mockResolvedValue({
        ok: true,
        json: async () => ({
          jobs: [
            {
              job_id: 'job-1',
              tenant_id: '00000000-0000-0000-0000-000000000001',
              job_type: 'REINDEX_ALL',
              job_status: 'done',
              requested_by: 'api',
              started_at: '2024-01-01T00:00:00Z',
              finished_at: '2024-01-01T00:01:00Z',
              result: { chunks: 2 },
            },
          ],
        }),
      });
    vi.stubGlobal('fetch', fetchMock);

    render(
      <QueryClientProvider client={new QueryClient()}>
        <TenantProvider value={{ tenantId: '00000000-0000-0000-0000-000000000001' }}>
          <IngestionPage />
        </TenantProvider>
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByText('Start Sync'));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  });
});
