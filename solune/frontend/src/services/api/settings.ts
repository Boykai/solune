import type {
  EffectiveUserSettings,
  UserPreferencesUpdate,
  GlobalSettings,
  GlobalSettingsUpdate,
  EffectiveProjectSettings,
  ProjectSettingsUpdate,
  ModelsResponse,
} from '@/types';
import { request } from './client';
import { EffectiveUserSettingsSchema } from '@/services/schemas/settings';
import { validateResponse } from '@/services/schemas/validate';

export const settingsApi = {
  /**
   * Get authenticated user's effective settings (merged with global defaults).
   */
  async getUserSettings(): Promise<EffectiveUserSettings> {
    const data = await request<EffectiveUserSettings>('/settings/user');
    return validateResponse(EffectiveUserSettingsSchema, data, 'settingsApi.getUserSettings');
  },

  /**
   * Update authenticated user's preferences (partial update).
   */
  updateUserSettings(data: UserPreferencesUpdate): Promise<EffectiveUserSettings> {
    return request<EffectiveUserSettings>('/settings/user', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * Get global/instance-level settings.
   */
  getGlobalSettings(): Promise<GlobalSettings> {
    return request<GlobalSettings>('/settings/global');
  },

  /**
   * Update global/instance-level settings (partial update).
   */
  updateGlobalSettings(data: GlobalSettingsUpdate): Promise<GlobalSettings> {
    return request<GlobalSettings>('/settings/global', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * Get effective project settings for authenticated user.
   */
  getProjectSettings(projectId: string): Promise<EffectiveProjectSettings> {
    return request<EffectiveProjectSettings>(`/settings/project/${projectId}`);
  },

  /**
   * Update per-project settings for authenticated user (partial update).
   */
  updateProjectSettings(
    projectId: string,
    data: ProjectSettingsUpdate
  ): Promise<EffectiveProjectSettings> {
    return request<EffectiveProjectSettings>(`/settings/project/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * Fetch available models for a provider (dynamic dropdown population).
   *
   * Accepts an optional `RequestInit` so callers (e.g. TanStack Query) can
   * pass an `AbortSignal` for request cancellation.
   */
  fetchModels(provider: string, forceRefresh = false, init?: RequestInit): Promise<ModelsResponse> {
    const params = forceRefresh ? '?force_refresh=true' : '';
    return request<ModelsResponse>(`/settings/models/${provider}${params}`, init);
  },
};
