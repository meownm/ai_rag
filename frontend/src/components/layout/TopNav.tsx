import { useTenant } from '@/providers/TenantProvider';

export function TopNav() {
  const { tenantId } = useTenant();
  return (
    <header className="flex h-14 items-center justify-between border-b bg-white px-4">
      <h1 className="font-semibold">Corporate RAG Console</h1>
      <p className="text-xs text-slate-500">Tenant: {tenantId}</p>
    </header>
  );
}
