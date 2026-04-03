import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

vi.mock('@/services/api', () => ({
  modelsApi: {
    list: vi.fn(),
  },
  settingsApi: {
    fetchModels: vi.fn(),
  },
}));

import * as api from '@/services/api';
import { useModels, expandReasoningModels } from './useModels';

const mockModelsApi = api.modelsApi as unknown as {
  list: ReturnType<typeof vi.fn>;
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

const mockModels = [
  { id: 'gpt-4o', name: 'GPT-4o', provider: 'openai' },
  { id: 'gpt-4o-mini', name: 'GPT-4o Mini', provider: 'openai' },
  { id: 'claude-3-5', name: 'Claude 3.5', provider: 'anthropic' },
];

describe('useModels', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns model list on success', async () => {
    mockModelsApi.list.mockResolvedValue(mockModels);

    const { result } = renderHook(() => useModels(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.models).toEqual(mockModels);
    expect(result.current.error).toBeNull();
  });

  it('groups models by provider', async () => {
    mockModelsApi.list.mockResolvedValue(mockModels);

    const { result } = renderHook(() => useModels(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.models.length).toBe(3));

    const groups = result.current.modelsByProvider;
    expect(groups).toHaveLength(2);

    const openaiGroup = groups.find((g) => g.provider === 'openai');
    expect(openaiGroup?.models).toHaveLength(2);

    const anthropicGroup = groups.find((g) => g.provider === 'anthropic');
    expect(anthropicGroup?.models).toHaveLength(1);
  });

  it('returns empty array when no data', async () => {
    mockModelsApi.list.mockResolvedValue([]);

    const { result } = renderHook(() => useModels(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.models).toEqual([]);
    expect(result.current.modelsByProvider).toEqual([]);
  });

  it('returns error message on failure', async () => {
    mockModelsApi.list.mockRejectedValue(new Error('Unable to load models'));

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    // Override retry at QueryClient level; the hook sets retry:2 but
    // we need immediate failure for testing
    function FailWrapper({ children }: { children: ReactNode }) {
      return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
    }

    const { result } = renderHook(() => useModels(), {
      wrapper: FailWrapper,
    });

    await waitFor(() => expect(result.current.error).toBe('Unable to load models'), {
      timeout: 5000,
    });
    expect(result.current.models).toEqual([]);
  });

  it('exposes refreshModels function', async () => {
    mockModelsApi.list.mockResolvedValue(mockModels);

    const { result } = renderHook(() => useModels(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(typeof result.current.refreshModels).toBe('function');
  });

  it('expands reasoning-capable models into per-level variants', async () => {
    const modelsWithReasoning = [
      {
        id: 'o3',
        name: 'o3',
        provider: 'openai',
        supported_reasoning_efforts: ['low', 'medium', 'high'],
        default_reasoning_effort: 'medium',
      },
      { id: 'gpt-4o', name: 'GPT-4o', provider: 'openai' },
    ];
    mockModelsApi.list.mockResolvedValue(modelsWithReasoning);

    const { result } = renderHook(() => useModels(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    // 3 expanded from o3 + 1 gpt-4o = 4
    expect(result.current.models).toHaveLength(4);
    expect(result.current.models[0]).toMatchObject({
      id: 'o3',
      name: 'o3 (Low)',
      reasoning_effort: 'low',
    });
    expect(result.current.models[1]).toMatchObject({
      id: 'o3',
      name: 'o3 (Medium)',
      reasoning_effort: 'medium',
    });
    expect(result.current.models[2]).toMatchObject({
      id: 'o3',
      name: 'o3 (High)',
      reasoning_effort: 'high',
    });
    // Non-reasoning model passes through unchanged
    expect(result.current.models[3]).toMatchObject({
      id: 'gpt-4o',
      name: 'GPT-4o',
    });
    expect(result.current.models[3].reasoning_effort).toBeUndefined();
  });
});

describe('expandReasoningModels', () => {
  it('passes through models without reasoning support unchanged', () => {
    const models = [
      { id: 'gpt-4o', name: 'GPT-4o', provider: 'openai' },
      { id: 'claude-3', name: 'Claude 3', provider: 'anthropic' },
    ];
    const result = expandReasoningModels(models);
    expect(result).toEqual(models);
  });

  it('expands models with reasoning support into per-level variants', () => {
    const models = [
      {
        id: 'o3',
        name: 'o3',
        provider: 'openai',
        supported_reasoning_efforts: ['low', 'high', 'xhigh'],
        default_reasoning_effort: 'high',
      },
    ];
    const result = expandReasoningModels(models);
    expect(result).toHaveLength(3);
    expect(result[0]).toMatchObject({ id: 'o3', name: 'o3 (Low)', reasoning_effort: 'low' });
    expect(result[1]).toMatchObject({ id: 'o3', name: 'o3 (High)', reasoning_effort: 'high' });
    expect(result[2]).toMatchObject({ id: 'o3', name: 'o3 (XHigh)', reasoning_effort: 'xhigh' });
  });

  it('handles mixed models (some with reasoning, some without)', () => {
    const models = [
      {
        id: 'o3',
        name: 'o3',
        provider: 'openai',
        supported_reasoning_efforts: ['medium', 'high'],
      },
      { id: 'gpt-4o', name: 'GPT-4o', provider: 'openai' },
    ];
    const result = expandReasoningModels(models);
    expect(result).toHaveLength(3);
    expect(result[0].reasoning_effort).toBe('medium');
    expect(result[1].reasoning_effort).toBe('high');
    expect(result[2].reasoning_effort).toBeUndefined();
  });

  it('returns empty array for empty input', () => {
    expect(expandReasoningModels([])).toEqual([]);
  });

  it('preserves original model properties in expanded variants', () => {
    const models = [
      {
        id: 'o3',
        name: 'o3',
        provider: 'openai',
        supported_reasoning_efforts: ['high'],
        default_reasoning_effort: 'high',
        cost_tier: 'premium' as const,
      },
    ];
    const result = expandReasoningModels(models);
    expect(result[0].cost_tier).toBe('premium');
    expect(result[0].default_reasoning_effort).toBe('high');
  });
});
