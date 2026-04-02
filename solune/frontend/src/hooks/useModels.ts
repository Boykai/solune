/**
 * useModels — fetch and cache available AI models with provider grouping.
 *
 * Reasoning-capable models are expanded into per-level variants with display
 * names like "o3 (High)" and a populated `reasoning_effort` field.
 */

import { useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { modelsApi } from '@/services/api';
import type { AIModel, ModelGroup } from '@/types';

export const modelKeys = {
  all: ['models'] as const,
  copilot: () => [...modelKeys.all, 'copilot'] as const,
};

export async function fetchCopilotModels(forceRefresh = false): Promise<AIModel[]> {
  return modelsApi.list(forceRefresh);
}

/**
 * Expand reasoning-capable models into per-level variants.
 *
 * For each model with `supported_reasoning_efforts`, generates N `AIModel`
 * entries — one per reasoning level — with `name: "{name} ({Level})"` and
 * `reasoning_effort` set. Non-reasoning models pass through unchanged.
 */
export function expandReasoningModels(raw: AIModel[]): AIModel[] {
  const expanded: AIModel[] = [];
  for (const model of raw) {
    if (model.supported_reasoning_efforts?.length) {
      for (const level of model.supported_reasoning_efforts) {
        expanded.push({
          ...model,
          name: `${model.name} (${level.charAt(0).toUpperCase() + level.slice(1)})`,
          reasoning_effort: level,
        });
      }
    } else {
      expanded.push(model);
    }
  }
  return expanded;
}

export function useModels() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery<AIModel[]>({
    queryKey: modelKeys.copilot(),
    queryFn: () => fetchCopilotModels(false),
    staleTime: Infinity,
    gcTime: Infinity,
    retry: 2,
  });

  const refreshMutation = useMutation({
    mutationFn: () => fetchCopilotModels(true),
    onSuccess: (freshModels) => {
      queryClient.setQueryData(modelKeys.copilot(), freshModels);
    },
  });

  const models = useMemo(() => expandReasoningModels(data ?? []), [data]);

  const modelsByProvider = useMemo<ModelGroup[]>(() => {
    const groups = new Map<string, AIModel[]>();
    for (const model of models) {
      const existing = groups.get(model.provider) ?? [];
      existing.push(model);
      groups.set(model.provider, existing);
    }
    return Array.from(groups.entries()).map(([provider, providerModels]) => ({
      provider,
      models: providerModels,
    }));
  }, [models]);

  return {
    models,
    modelsByProvider,
    isLoading,
    isRefreshing: refreshMutation.isPending,
    refreshModels: () => refreshMutation.mutateAsync(),
    error: error ? (error as Error).message : null,
  };
}
