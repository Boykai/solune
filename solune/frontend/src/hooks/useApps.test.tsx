import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { createMockApi, type MockApiShape } from '@/test/setup';

vi.mock('@/services/api', () => createMockApi());

import * as api from '@/services/api';
import { useApps, useCreateApp, useDeleteApp, isApiError, getErrorMessage } from './useApps';

const mockApi = api as unknown as MockApiShape;
const mockAppsApi = mockApi.appsApi;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

const mockApp = {
  name: 'my-app',
  display_name: 'My App',
  status: 'running',
  description: 'A test app',
};

describe('useApps', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns apps list on success', async () => {
    mockAppsApi.list.mockResolvedValue([mockApp]);

    const { result } = renderHook(() => useApps(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([mockApp]);
  });

  it('handles error', async () => {
    mockAppsApi.list.mockRejectedValue(new Error('Failed'));

    const { result } = renderHook(() => useApps(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useCreateApp', () => {
  beforeEach(() => vi.clearAllMocks());

  it('calls create API', async () => {
    mockAppsApi.create.mockResolvedValue(mockApp);

    const { result } = renderHook(() => useCreateApp(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({ name: 'my-app', display_name: 'My App' } as never);
    });

    expect(mockAppsApi.create).toHaveBeenCalled();
  });
});

describe('useDeleteApp', () => {
  beforeEach(() => vi.clearAllMocks());

  it('calls delete API', async () => {
    mockAppsApi.delete.mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteApp(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({ appName: 'my-app' });
    });

    expect(mockAppsApi.delete).toHaveBeenCalledWith('my-app', undefined);
  });
});

describe('isApiError', () => {
  it('returns true for ApiError instances', () => {
    const err = new api.ApiError(500, { error: 'Server error' });
    expect(isApiError(err)).toBe(true);
  });

  it('returns false for regular Error', () => {
    expect(isApiError(new Error('oops'))).toBe(false);
  });

  it('returns false for non-error values', () => {
    expect(isApiError('string')).toBe(false);
    expect(isApiError(null)).toBe(false);
  });
});

describe('getErrorMessage', () => {
  it('extracts message from ApiError', () => {
    const err = new api.ApiError(400, { error: 'Bad request' });
    expect(getErrorMessage(err, 'fallback')).toBe('Bad request');
  });

  it('extracts message from regular Error', () => {
    expect(getErrorMessage(new Error('oops'), 'fallback')).toBe('oops');
  });

  it('returns fallback for unknown errors', () => {
    expect(getErrorMessage(42, 'fallback')).toBe('fallback');
    expect(getErrorMessage(undefined, 'fallback')).toBe('fallback');
  });
});
