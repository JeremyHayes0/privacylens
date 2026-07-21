import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import * as authApi from "../api/auth";
import { setAuthToken } from "../api/client";
import type { User } from "../api/types";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, organizationName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// SESSION_STORAGE_KEY holds only the access token, and only in
// sessionStorage (cleared when the tab closes) rather than
// localStorage (persists indefinitely). The token itself lives in
// memory during the session -- see api/client.ts's setAuthToken --
// this is purely so a page refresh doesn't force a fresh login. The
// backend has no refresh-token/revocation mechanism yet (see the
// backend README), so there's no way to invalidate a token before its
// 15-minute expiry regardless of where the frontend stores it; this
// is the frontend's half of that same tradeoff.
const SESSION_STORAGE_KEY = "privacylens_token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!storedToken) {
      setIsLoading(false);
      return;
    }

    setAuthToken(storedToken);
    authApi
      .fetchCurrentUser()
      .then(setUser)
      .catch(() => {
        // Stored token is expired, invalid, or the account was
        // deactivated -- treat it as "not logged in" rather than
        // surfacing an error on app load.
        sessionStorage.removeItem(SESSION_STORAGE_KEY);
        setAuthToken(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await authApi.login({ email, password });
    sessionStorage.setItem(SESSION_STORAGE_KEY, access_token);
    setAuthToken(access_token);
    setUser(await authApi.fetchCurrentUser());
  }, []);

  const register = useCallback(
    async (email: string, password: string, organizationName?: string) => {
      await authApi.register({ email, password, organization_name: organizationName });
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(() => {
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
    setAuthToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
