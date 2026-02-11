import { createContext, useContext } from 'react';

type AuthContextValue = {
  userId: string;
};

const AuthContext = createContext<AuthContextValue>({ userId: 'local-user' });

export const AuthProvider = AuthContext.Provider;

export const useAuth = () => useContext(AuthContext);
