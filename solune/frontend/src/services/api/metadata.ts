import type {
  RepositoryMetadata,
  SignalConnection,
  SignalLinkResponse,
  SignalLinkStatusResponse,
  SignalPreferences,
  SignalPreferencesUpdate,
  SignalBannersResponse,
} from '@/types';
import { request } from './client';

export const metadataApi = {
  /**
   * Get cached repository metadata (labels, branches, milestones, collaborators).
   */
  getMetadata(owner: string, repo: string): Promise<RepositoryMetadata> {
    return request<RepositoryMetadata>(`/metadata/${owner}/${repo}`);
  },

  /**
   * Force-refresh repository metadata from the GitHub API.
   */
  refreshMetadata(owner: string, repo: string): Promise<RepositoryMetadata> {
    return request<RepositoryMetadata>(`/metadata/${owner}/${repo}/refresh`, {
      method: 'POST',
    });
  },
};

export const signalApi = {
  /**
   * Get current Signal connection status.
   */
  getConnection(): Promise<SignalConnection> {
    return request<SignalConnection>('/signal/connection');
  },

  /**
   * Initiate Signal QR code linking flow.
   */
  initiateLink(deviceName = 'Solune'): Promise<SignalLinkResponse> {
    return request<SignalLinkResponse>('/signal/connection/link', {
      method: 'POST',
      body: JSON.stringify({ device_name: deviceName }),
    });
  },

  /**
   * Poll linking status after QR code display.
   */
  checkLinkStatus(): Promise<SignalLinkStatusResponse> {
    return request<SignalLinkStatusResponse>('/signal/connection/link/status');
  },

  /**
   * Disconnect Signal account.
   */
  disconnect(): Promise<{ message: string }> {
    return request<{ message: string }>('/signal/connection', {
      method: 'DELETE',
    });
  },

  /**
   * Get Signal notification preferences.
   */
  getPreferences(): Promise<SignalPreferences> {
    return request<SignalPreferences>('/signal/preferences');
  },

  /**
   * Update Signal notification preferences.
   */
  updatePreferences(data: SignalPreferencesUpdate): Promise<SignalPreferences> {
    return request<SignalPreferences>('/signal/preferences', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * Get active Signal conflict banners.
   */
  getBanners(): Promise<SignalBannersResponse> {
    return request<SignalBannersResponse>('/signal/banners');
  },

  /**
   * Dismiss a conflict banner.
   */
  dismissBanner(bannerId: string): Promise<{ message: string }> {
    return request<{ message: string }>(`/signal/banners/${bannerId}/dismiss`, {
      method: 'POST',
    });
  },
};
