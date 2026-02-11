import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { QueryPage } from '@/pages/QueryPage';
import { TenantProvider } from '@/providers/TenantProvider';
import { RoleProvider } from '@/providers/RoleProvider';

function renderPage(roles: string[] = ['viewer']) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <TenantProvider value={{ tenantId: '00000000-0000-0000-0000-000000000001' }}>
        <RoleProvider value={{ roles }}>
          <QueryPage />
        </RoleProvider>
      </TenantProvider>
    </QueryClientProvider>,
  );
}

describe('QueryPage conversational UI', () => {
  it('renders assistant structured answer with sources', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          answer: 'Summary line\nDetailed line',
          only_sources_verdict: 'PASS',
          citations: [{ chunk_id: '1', document_id: 'd', title: 'Doc', url: 'u', snippet: 'Snippet' }],
          correlation_id: 'c',
        }),
      }),
    );

    renderPage();
    fireEvent.change(screen.getByPlaceholderText('Ask a question...'), { target: { value: 'what is policy' } });
    fireEvent.click(screen.getByText('Send'));

    await waitFor(() => expect(screen.getByText('Summary')).toBeInTheDocument());
    expect(screen.getAllByText('Doc').length).toBeGreaterThan(0);
  });

  it('shows clarification modal and blocks free-text path for ambiguous slash query', async () => {
    vi.stubGlobal('fetch', vi.fn());
    renderPage();

    fireEvent.change(screen.getByPlaceholderText('Ask a question...'), { target: { value: 'vacation/sick leave' } });
    fireEvent.click(screen.getByText('Send'));

    expect(screen.getByText('Уточните вопрос')).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('maps refusal message safely', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ error: { code: 'ONLY_SOURCES_VIOLATION', message: 'Policy blocked', correlation_id: 'c', retryable: false, timestamp: '2024-01-01T00:00:00Z' } }) }));
    renderPage();

    fireEvent.change(screen.getByPlaceholderText('Ask a question...'), { target: { value: 'secret?' } });
    fireEvent.click(screen.getByText('Send'));

    await waitFor(() => expect(screen.getByText('Policy blocked')).toBeInTheDocument());
    expect(screen.queryByText(/Traceback/)).not.toBeInTheDocument();
  });

  it('allows debug toggle for admin and renders debug fields', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ answer: 'Summary', only_sources_verdict: 'PASS', citations: [], correlation_id: 'c' }),
      }),
    );
    renderPage(['admin']);

    fireEvent.click(screen.getByText('Settings'));
    fireEvent.click(screen.getByLabelText('Debug transparency mode'));
    fireEvent.change(screen.getByPlaceholderText('Ask a question...'), { target: { value: 'q' } });
    fireEvent.click(screen.getByText('Send'));

    await waitFor(() => expect(screen.getByText(/Interpreted query/)).toBeInTheDocument());
  });
});
