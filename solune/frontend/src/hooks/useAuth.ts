/**
 * Authentication hook for GitHub OAuth.
 */

import { useCallback, useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi, ApiError, onAuthExpired } from '@/services/api';
import { STALE_TIME_LONG } from '@/constants';
import { fetchCopilotModels, modelKeys } from '@/hooks/useModels';
import type { User } from '@/types';

const LOGOUT_LOCAL_STORAGE_KEYS = [
  'chat-message-history',
  'solune-read-notifications',
  'solune-onboarding-completed',
  'solune-experimental-features',
  'chat-ai-enhance',
  'chat-popup-size',
  'sidebar-collapsed',
  'parentIssueIntake_expanded',
] as const;

const LOGOUT_LOCAL_STORAGE_PREFIXES = ['pipeline-config:', 'board-controls-'] as const;
const LOGOUT_SESSION_STORAGE_KEYS = ['solune-redirect-after-login', 'solune-chunk-reload'] as const;

function removeMatchingStorageKeys(
  storage: Storage,
  staticKeys: readonly string[],
  keyPrefixes: readonly string[] = []
): void {
  const storageKeys = Array.from({ length: storage.length }, (_, index) => storage.key(index)).filter(
    (key): key is string => key !== null
  );

  for (const key of [
    ...staticKeys,
    ...storageKeys.filter((key) => keyPrefixes.some((prefix) => key.startsWith(prefix))),
  ]) {
    storage.removeItem(key);
  }
}

function clearUserStorage(): void {
  try {
    removeMatchingStorageKeys(
      localStorage,
      LOGOUT_LOCAL_STORAGE_KEYS,
      LOGOUT_LOCAL_STORAGE_PREFIXES
    );
  } catch {
    // Ignore storage errors
  }

  try {
    removeMatchingStorageKeys(sessionStorage, LOGOUT_SESSION_STORAGE_KEYS);
  } catch {
    // Ignore storage errors
  }
}

interface UseAuthReturn {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: Error | null;
  login: () => void;
  logout: () => Promise<void>;
  refetch: () => void;
}

export function useAuth(): UseAuthReturn {
  const queryClient = useQueryClient();
  const [error, setError] = useState<Error | null>(null);

  // After OAuth callback redirect, the cookie is already set by the backend.
  // Clean the URL path if we landed on /auth/callback so the user sees a clean URL.
  // We use replaceState to update the browser URL and then dispatch a popstate event
  // so that React Router (createBrowserRouter) re-evaluates the current path — without
  // this dispatch, the router keeps the /auth/callback URL in its internal state and
  // matches the * wildcard, rendering NotFoundPage instead of the home page.
  useEffect(() => {
    if (window.location.pathname === '/auth/callback') {
      window.history.replaceState({}, '', '/');
      window.dispatchEvent(new PopStateEvent('popstate', { state: window.history.state }));
      // Refetch user to pick up the new session cookie
      queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
    }
  }, [queryClient]);

  const {
    data: user,
    isLoading: queryLoading,
    isFetched,
    error: queryError,
    refetch,
  } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: authApi.getCurrentUser,
    retry: false,
    staleTime: STALE_TIME_LONG,
  });

  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      queryClient.setQueryData(['auth', 'me'], null);
      queryClient.removeQueries({ queryKey: modelKeys.all });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['chat'] });
      clearUserStorage();
    },
    onError: (err) => {
      setError(err as Error);
    },
  });

  const login = useCallback(() => {
    authApi.login();
  }, []);

  const logout = useCallback(async () => {
    await logoutMutation.mutateAsync();
  }, [logoutMutation]);

  useEffect(() => {
    if (!user) return;
    void queryClient.prefetchQuery({
      queryKey: modelKeys.copilot(),
      queryFn: () => fetchCopilotModels(true),
      staleTime: Infinity,
    });
  }, [queryClient, user]);

  // Handle auth errors (401 means not logged in, which is expected)
  const [prevQueryError, setPrevQueryError] = useState(queryError);
  if (queryError !== prevQueryError) {
    setPrevQueryError(queryError);
    if (queryError && !(queryError instanceof ApiError && queryError.status === 401)) {
      setError(queryError as Error);
    }
  }

  // Auto-logout: when any API call returns 401 (session/token expired),
  // clear the cached user so the app shows the login screen immediately
  // instead of leaving the user stuck on a broken board page.
  useEffect(() => {
    return onAuthExpired(() => {
      queryClient.setQueryData(['auth', 'me'], null);
      queryClient.removeQueries({ queryKey: modelKeys.all });
      queryClient.invalidateQueries({ queryKey: ['board'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['chat'] });
    });
  }, [queryClient]);

  // Consider loading done if we got a 401 (not authenticated) or if query completed
  const is401Error = queryError instanceof ApiError && queryError.status === 401;
  const isLoading = queryLoading && !is401Error && !isFetched;

  return {
    user: user ?? null,
    isLoading,
    isAuthenticated: !!user,
    error,
    login,
    logout,
    refetch,
  };
}
