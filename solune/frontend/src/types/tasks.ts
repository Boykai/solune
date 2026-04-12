/**
 * Task domain types.
 */

export interface Task {
  task_id: string;
  project_id: string;
  github_item_id: string;
  github_content_id?: string;
  title: string;
  description?: string;
  status: string;
  status_option_id: string;
  assignees?: string[];
  labels?: Array<{ name: string; color: string }>;
  created_at: string;
  updated_at: string;
}

export interface TaskCreateRequest {
  project_id: string;
  title: string;
  description?: string;
}

export interface TaskListResponse {
  tasks: Task[];
}
