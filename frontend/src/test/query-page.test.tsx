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
  it('shows refusal message from refusal json', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ error: { code: 'ONLY_SOURCES_VIOLATION', message: 'Policy blocked', correlation_id: 'c', retryable: false, timestamp: '2024-01-01T00:00:00Z' } }) }));
    renderPage();
    fireEvent.change(screen.getByPlaceholderText('Ask a question...'), { target: { value: 'secret?' } });
    fireEvent.click(screen.getByText('Search'));
    await waitFor(() => expect(screen.getByText(/Refusal: Policy blocked/)).toBeInTheDocument());
  });
});
