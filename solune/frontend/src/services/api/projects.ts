import type { Project, ProjectListResponse } from '@/types';
import type { CreateProjectRequest, CreateProjectResponse } from '@/types/apps';
import type { User } from '@/types';
import { request } from './client';
import { ProjectListResponseSchema } from '@/services/schemas/projects';
import { validateResponse } from '@/services/schemas/validate';

export const projectsApi = {
  /**
   * List all accessible GitHub Projects.
   */
  async list(refresh = false): Promise<ProjectListResponse> {
    const params = refresh ? '?refresh=true' : '';
    const data = await request<ProjectListResponse>(`/projects${params}`);
    return validateResponse(ProjectListResponseSchema, data, 'projectsApi.list');
  },

  /**
   * Get project details including items.
   */
  get(projectId: string): Promise<Project> {
    return request<Project>(`/projects/${projectId}`);
  },

  /**
   * Select a project as the active project.
   */
  select(projectId: string): Promise<User> {
    return request<User>(`/projects/${projectId}/select`, {
      method: 'POST',
    });
  },

  /**
   * Create a standalone GitHub Project V2.
   */
  create(data: CreateProjectRequest): Promise<CreateProjectResponse> {
    return request<CreateProjectResponse>('/projects/create', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};
