import type { Task, TaskCreateRequest, TaskListResponse } from '@/types';
import { request } from './client';

export const tasksApi = {
  /**
   * List tasks for a project.
   */
  listByProject(projectId: string): Promise<TaskListResponse> {
    return request<TaskListResponse>(`/projects/${projectId}/tasks`);
  },

  /**
   * Create a new task.
   */
  create(data: TaskCreateRequest): Promise<Task> {
    return request<Task>('/tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update task status.
   */
  updateStatus(taskId: string, status: string): Promise<Task> {
    return request<Task>(`/tasks/${taskId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },
};
