import type { BoardProjectListResponse, BoardDataResponse } from '@/types';
import { request } from './client';
import { BoardDataResponseSchema } from '@/services/schemas/board';
import { validateResponse } from '@/services/schemas/validate';

export const boardApi = {
  /**
   * List available projects for board display.
   */
  listProjects(refresh = false): Promise<BoardProjectListResponse> {
    const params = refresh ? '?refresh=true' : '';
    return request<BoardProjectListResponse>(`/board/projects${params}`);
  },

  /**
   * Get board data for a specific project.
   */
  async getBoardData(projectId: string, refresh = false): Promise<BoardDataResponse> {
    const params = refresh ? '?refresh=true' : '';
    const data = await request<BoardDataResponse>(`/board/projects/${projectId}${params}`);
    return validateResponse(BoardDataResponseSchema, data, 'boardApi.getBoardData');
  },

  /**
   * Get board data with per-column pagination.
   */
  async getBoardDataPaginated(
    projectId: string,
    columnLimit: number,
    columnCursors?: Record<string, string>,
    refresh = false,
  ): Promise<BoardDataResponse> {
    const qs = new URLSearchParams({ column_limit: String(columnLimit) });
    if (refresh) qs.set('refresh', 'true');
    if (columnCursors && Object.keys(columnCursors).length > 0) {
      qs.set('column_cursors', JSON.stringify(columnCursors));
    }
    const data = await request<BoardDataResponse>(`/board/projects/${projectId}?${qs}`);
    return validateResponse(BoardDataResponseSchema, data, 'boardApi.getBoardDataPaginated');
  },

  /**
   * Update a board item's status by name.
   */
  updateItemStatus(
    projectId: string,
    itemId: string,
    status: string,
  ): Promise<{ success: boolean }> {
    return request<{ success: boolean }>(
      `/board/projects/${projectId}/items/${itemId}/status`,
      {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      },
    );
  },
};
