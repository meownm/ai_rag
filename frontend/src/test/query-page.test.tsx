import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { QueryPage } from '@/pages/QueryPage';
import { TenantProvider } from '@/providers/TenantProvider';
import { RoleProvider } from '@/providers/RoleProvider';

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <TenantProvider value={{ tenantId: '00000000-0000-0000-0000-000000000001' }}>
        <RoleProvider value={{ roles: ['viewer'] }}>
          <QueryPage />
        </RoleProvider>
      </TenantProvider>
    </QueryClientProvider>,
  );
}

describe('QueryPage refusal', () => {
  it('shows refusal message from refusal json in error response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({
          error: {
            code: 'ONLY_SOURCES_VIOLATION',
            message: 'Policy blocked',
            correlation_id: 'c',
            retryable: false,
            timestamp: '2024-01-01T00:00:00Z',
          },
        }),
      }),
    );

    renderPage();
    fireEvent.change(screen.getByPlaceholderText('Ask a question...'), { target: { value: 'secret?' } });
    fireEvent.click(screen.getByText('Search'));

    await waitFor(() => expect(screen.getByText(/Refusal: Policy blocked/)).toBeInTheDocument());
  });

  it('shows refusal message from refusal json string in successful response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          answer:
            '{"error":{"code":"ONLY_SOURCES_VIOLATION","message":"Use only provided sources","correlation_id":"corr-1","retryable":false,"timestamp":"2024-01-01T00:00:00Z"}}',
          only_sources_verdict: 'FAIL',
          citations: [],
          correlation_id: 'corr-1',
        }),
      }),
    );

    renderPage();
    fireEvent.change(screen.getByPlaceholderText('Ask a question...'), { target: { value: 'secret?' } });
    fireEvent.click(screen.getByText('Search'));

    await waitFor(() => expect(screen.getByText(/Refusal: Use only provided sources/)).toBeInTheDocument());
  });

  it('sends citations=true in query requests', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        answer: 'Safe answer',
        only_sources_verdict: 'PASS',
        citations: [],
        correlation_id: 'corr-2',
      }),
    });
    vi.stubGlobal('fetch', fetchSpy);

    renderPage();
    fireEvent.change(screen.getByPlaceholderText('Ask a question...'), { target: { value: 'what is rag?' } });
    fireEvent.click(screen.getByText('Search'));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));

    const [, request] = fetchSpy.mock.calls[0];
    const body = JSON.parse((request as RequestInit).body as string) as { citations?: boolean };
    expect(body.citations).toBe(true);
  });
});
