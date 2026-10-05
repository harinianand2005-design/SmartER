import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { api } from "../services/api";

export type UserRole = "ADMIN" | "TRIAGE_NURSE" | "HEALTH_AUTHORITY";
export type User = { id: number; email: string; full_name: string; role: UserRole; is_active: boolean };
type AuthContextValue = { user: User | null; token: string | null; isLoading: boolean; login: (email: string, password: string) => Promise<User>; logout: () => void };
const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const TOKEN_KEY = "smarter_access_token";
const USER_KEY = "smarter_user";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(() => { const stored = localStorage.getItem(USER_KEY); return stored ? JSON.parse(stored) as User : null; });
  const [isLoading, setIsLoading] = useState(Boolean(token && !user));

  useEffect(() => {
    if (!token) return;
    api.get<User>("/api/v1/auth/me", { headers: { Authorization: `Bearer ${token}` } })
      .then(({ data }) => { setUser(data); localStorage.setItem(USER_KEY, JSON.stringify(data)); })
      .catch(() => { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); setToken(null); setUser(null); })
      .finally(() => setIsLoading(false));
  }, [token]);

  async function login(email: string, password: string) {
    const { data } = await api.post<{ access_token: string; user: User }>("/api/v1/auth/login", { email, password });
    localStorage.setItem(TOKEN_KEY, data.access_token); localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    setToken(data.access_token); setUser(data.user); return data.user;
  }

  function logout() { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); setToken(null); setUser(null); }
  return <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>{children}</AuthContext.Provider>;
}

// The hook intentionally lives beside its provider so consumers share one auth contract.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() { const context = useContext(AuthContext); if (!context) throw new Error("useAuth must be used within AuthProvider"); return context; }