import { createContext, useContext } from 'react';

type TenantContextValue = {
  tenantId: string;
};

const TenantContext = createContext<TenantContextValue>({
  tenantId: '00000000-0000-0000-0000-000000000001',
});

export const TenantProvider = TenantContext.Provider;

export const useTenant = () => useContext(TenantContext);
