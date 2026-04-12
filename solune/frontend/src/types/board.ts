/**
 * Board domain types.
 */

import type { StatusColor, RateLimitInfo } from './common';

export type ContentType = 'issue' | 'draft_issue' | 'pull_request';

export type PRState = 'open' | 'closed' | 'merged';

export interface BoardStatusOption {
  option_id: string;
  name: string;
  color: StatusColor;
  description?: string;
}

export interface BoardStatusField {
  field_id: string;
  options: BoardStatusOption[];
}

export interface BoardProject {
  project_id: string;
  name: string;
  description?: string;
  url: string;
  owner_login: string;
  status_field: BoardStatusField;
}

export interface BoardRepository {
  owner: string;
  name: string;
}

export interface BoardAssignee {
  login: string;
  avatar_url: string;
}

export interface BoardCustomFieldValue {
  name: string;
  color?: StatusColor;
}

export interface LinkedPR {
  pr_id: string;
  number: number;
  title: string;
  state: PRState;
  url: string;
}

export interface BoardLabel {
  id: string;
  name: string;
  color: string;
}

export interface SubIssue {
  id: string;
  number: number;
  title: string;
  url: string;
  state: string;
  assigned_agent?: string | null;
  assignees: BoardAssignee[];
  linked_prs: LinkedPR[];
}

export interface BoardItem {
  item_id: string;
  content_id?: string;
  content_type: ContentType;
  title: string;
  number?: number;
  repository?: BoardRepository;
  url?: string;
  body?: string;
  status: string;
  status_option_id: string;
  assignees: BoardAssignee[];
  priority?: BoardCustomFieldValue;
  size?: BoardCustomFieldValue;
  estimate?: number;
  linked_prs: LinkedPR[];
  sub_issues: SubIssue[];
  labels: BoardLabel[];
  issue_type?: string;
  created_at?: string;
  updated_at?: string;
  milestone?: string;
  queued?: boolean;
}

export interface BoardColumn {
  status: BoardStatusOption;
  items: BoardItem[];
  item_count: number;
  estimate_total: number;
  next_cursor?: string | null;
  has_more?: boolean;
}

export interface BoardDataResponse {
  project: BoardProject;
  columns: BoardColumn[];
  rate_limit?: RateLimitInfo | null;
}

export interface BoardProjectListResponse {
  projects: BoardProject[];
  rate_limit?: RateLimitInfo | null;
}
