import { createContext, useContext } from 'react';

export type UserRole = 'viewer' | 'admin' | 'debug';

type RoleContextValue = {
  roles: UserRole[];
};

const RoleContext = createContext<RoleContextValue>({ roles: ['viewer'] });

export const RoleProvider = RoleContext.Provider;

export const useRoles = () => useContext(RoleContext);
