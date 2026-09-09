import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useState, type PropsWithChildren } from "react";

import { queryClient } from "../../app/queryClient";
import { ApiClientError, getMe, logout } from "./api";
import type { AuthStatus, MeResponse } from "./types";

interface AuthContextValue {
  status: AuthStatus;
  user?: MeResponse;
  error?: Error;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function isNetworkError(error: unknown): boolean {
  return error instanceof TypeError;
}

function AuthStateProvider({ children }: PropsWithChildren) {
  const [signedOut, setSignedOut] = useState(false);
  const meQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: getMe,
    retry: (failureCount, error) => isNetworkError(error) && failureCount < 2,
  });

  const refresh = useCallback(async () => {
    setSignedOut(false);
    await queryClient.fetchQuery({ queryKey: ["auth", "me"], queryFn: getMe, staleTime: 0 });
  }, []);

  const signOut = useCallback(async () => {
    try {
      await logout();
    } finally {
      queryClient.clear();
      setSignedOut(true);
    }
  }, []);

  let status: AuthStatus = signedOut ? "anonymous" : "loading";
  if (!signedOut && meQuery.isSuccess) status = "authenticated";
  if (!signedOut && meQuery.isError && meQuery.error instanceof ApiClientError) {
    status = meQuery.error.status === 403 ? "forbidden" : "anonymous";
  }
  if (!signedOut && meQuery.isError && !(meQuery.error instanceof ApiClientError)) status = "anonymous";

  return (
    <AuthContext.Provider value={{
      status,
      user: meQuery.data,
      error: meQuery.error ?? undefined,
      refresh,
      signOut,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function AuthProvider({ children }: PropsWithChildren) {
  return <QueryClientProvider client={queryClient}><AuthStateProvider>{children}</AuthStateProvider></QueryClientProvider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
