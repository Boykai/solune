import type { AIModel } from '@/types';
import { settingsApi } from './settings';

export const modelsApi = {
  async list(forceRefresh = false): Promise<AIModel[]> {
    const response = await settingsApi.fetchModels('copilot', forceRefresh);
    // Treat non-success responses with no models as an error so TanStack Query
    // retries on subsequent mounts rather than permanently caching an empty list.
    if (response.status !== 'success' && !response.models?.length) {
      throw new Error(response.message ?? `Unable to load models: ${response.status}`);
    }
    return (response.models ?? []).map((model) => ({
      id: model.id,
      name: model.name,
      provider: model.provider,
      supported_reasoning_efforts: model.supported_reasoning_efforts,
      default_reasoning_effort: model.default_reasoning_effort,
    }));
  },
};
