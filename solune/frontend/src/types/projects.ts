/**
 * Project domain types.
 */

export type ProjectType = 'organization' | 'user' | 'repository';

export interface StatusColumn {
  field_id: string;
  name: string;
  option_id: string;
  color?: string;
}

export interface Project {
  project_id: string;
  owner_id: string;
  owner_login: string;
  name: string;
  type: ProjectType;
  url: string;
  description?: string;
  status_columns: StatusColumn[];
  item_count?: number;
  cached_at: string;
}

export interface ProjectListResponse {
  projects: Project[];
}
