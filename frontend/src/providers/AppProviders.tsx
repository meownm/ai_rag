import { PropsWithChildren } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/api/client';
import { AuthProvider } from './AuthProvider';
import { TenantProvider } from './TenantProvider';
import { RoleProvider } from './RoleProvider';

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider value={{ userId: 'local-user' }}>
        <TenantProvider value={{ tenantId: '00000000-0000-0000-0000-000000000001' }}>
          <RoleProvider value={{ roles: ['viewer'] }}>{children}</RoleProvider>
        </TenantProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
