import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { IngestionPage } from '@/pages/IngestionPage';
import { TenantProvider } from '@/providers/TenantProvider';

describe('IngestionPage', () => {
  it('starts ingestion and polls job status', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ job_id: 'job-1', job_status: 'queued' }) })
      .mockResolvedValue({ ok: true, json: async () => ({ job_id: 'job-1', tenant_id: 't', job_type: 'SYNC_CONFLUENCE', job_status: 'processing', requested_by: 'u', started_at: '2024-01-01T00:00:00Z' }) });
    vi.stubGlobal('fetch', fetchMock);

    render(
      <QueryClientProvider client={new QueryClient()}>
        <TenantProvider value={{ tenantId: '00000000-0000-0000-0000-000000000001' }}>
          <IngestionPage />
        </TenantProvider>
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByText('Start Sync'));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(screen.getByText('job-1')).toBeInTheDocument();
  });
});
