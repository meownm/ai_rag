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
          trace: { trace_id: 'c', scoring_trace: [{ chunk_id: '1', lex_score: 1, vec_score: 1, rerank_score: 1, boosts_applied: [], final_score: 0.77, rank_position: 1 }] },
        }),
      }),
    );

    renderPage();
    fireEvent.change(screen.getByPlaceholderText('Ask a question...'), { target: { value: 'what is policy' } });
    fireEvent.click(screen.getByText('Send'));

    await waitFor(() => expect(screen.getByText('Summary')).toBeInTheDocument());
    expect(screen.getAllByText('Doc').length).toBeGreaterThan(0);
    expect(screen.getByText('Details')).toBeInTheDocument();
    expect(screen.getAllByText('Sources').length).toBeGreaterThan(0);
  });

  it('shows clarification modal and uses radio + apply only flow', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ answer: 'Resolved', only_sources_verdict: 'PASS', citations: [], correlation_id: 'c' }) });
    vi.stubGlobal('fetch', fetchMock);
    renderPage();

    fireEvent.change(screen.getByPlaceholderText('Ask a question...'), { target: { value: 'vacation/sick leave' } });
    fireEvent.click(screen.getByText('Send'));

    expect(screen.getByText('Уточните вопрос')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByText('Применить')).toBeDisabled();

    fireEvent.click(screen.getByLabelText('sick leave'));
    fireEvent.click(screen.getByText('Применить'));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  });

  it('maps refusal message safely', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ error: { code: 'ONLY_SOURCES_VIOLATION', message: 'Policy blocked', correlation_id: 'c', retryable: false, timestamp: '2024-01-01T00:00:00Z' } }) }));
    renderPage();

    fireEvent.change(screen.getByPlaceholderText('Ask a question...'), { target: { value: 'secret?' } });
    fireEvent.click(screen.getByText('Send'));

    await waitFor(() => expect(screen.getByText('Policy blocked')).toBeInTheDocument());
    expect(screen.queryByText(/Traceback/)).not.toBeInTheDocument();
  });

  it('allows debug toggle for admin and renders debug fields with agent trace', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          answer: 'Summary',
          only_sources_verdict: 'PASS',
          citations: [],
          correlation_id: 'c',
          trace: {
            trace_id: 'c',
            scoring_trace: [
              { chunk_id: '1', lex_score: 1, vec_score: 1, rerank_score: 1, boosts_applied: [], final_score: 0.99, rank_position: 1 },
            ],
          },
        }),
      }),
    );
    renderPage(['admin']);

    fireEvent.click(screen.getByText('Settings'));
    fireEvent.click(screen.getByLabelText('Debug transparency mode'));
    fireEvent.change(screen.getByPlaceholderText('Ask a question...'), { target: { value: 'q' } });
    fireEvent.click(screen.getByText('Send'));

    await waitFor(() => expect(screen.getByText(/Interpreted query/)).toBeInTheDocument());
    expect(screen.getByText(/Agent trace/)).toBeInTheDocument();
    expect(screen.getByText(/Dynamic top_k/)).toBeInTheDocument();
    expect(screen.getByText(/Coverage ratio/)).toBeInTheDocument();
  });

  it('opens source preview modal with highlight', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          answer: 'Summary line',
          only_sources_verdict: 'PASS',
          citations: [{ chunk_id: '1', document_id: 'd', title: 'Doc', url: 'u', snippet: 'policy snippet only' }],
          correlation_id: 'c',
        }),
      }),
    );

    renderPage();
    fireEvent.change(screen.getByPlaceholderText('Ask a question...'), { target: { value: 'vacation policy' } });
    fireEvent.click(screen.getByText('Send'));

    await waitFor(() => expect(screen.getAllByText('Doc').length).toBeGreaterThan(0));
    fireEvent.click(screen.getAllByText('Doc')[0]);

    expect(screen.getByText('Закрыть')).toBeInTheDocument();
    expect(document.querySelector('mark')).not.toBeNull();
  });

  it('resets dialog state via New Dialog button', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ answer: 'Summary', only_sources_verdict: 'PASS', citations: [], correlation_id: 'c' }) }));
    renderPage();

    fireEvent.change(screen.getByPlaceholderText('Ask a question...'), { target: { value: 'vacation/sick leave' } });
    fireEvent.click(screen.getByText('Send'));
    expect(screen.getByText('Уточните вопрос')).toBeInTheDocument();

    fireEvent.click(screen.getByText('New Dialog'));
    await waitFor(() => expect(screen.queryByText('Уточните вопрос')).not.toBeInTheDocument());
  });

});
