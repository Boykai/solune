/**
 * Cleanup domain types.
 */

export interface BranchInfo {
  name: string;
  eligible_for_deletion: boolean;
  linked_issue_number: number | null;
  linked_issue_title: string | null;
  linking_method: string | null;
  preservation_reason: string | null;
  deletion_reason: string | null;
}

export interface PullRequestInfo {
  number: number;
  title: string;
  head_branch: string;
  referenced_issues: number[];
  eligible_for_deletion: boolean;
  preservation_reason: string | null;
  deletion_reason: string | null;
}

export interface OrphanedIssueInfo {
  number: number;
  title: string;
  labels: string[];
  html_url: string | null;
  node_id: string | null;
}

export interface IssueInfo {
  number: number;
  title: string;
  labels: string[];
  html_url: string | null;
  node_id: string | null;
  preservation_reason: string | null;
}

export interface IssueToDelete {
  number: number;
  node_id: string;
}

export interface CleanupPreflightResponse {
  branches_to_delete: BranchInfo[];
  branches_to_preserve: BranchInfo[];
  prs_to_close: PullRequestInfo[];
  prs_to_preserve: PullRequestInfo[];
  orphaned_issues: OrphanedIssueInfo[];
  issues_to_preserve: IssueInfo[];
  open_issues_on_board: number;
  has_permission: boolean;
  permission_error: string | null;
}

export interface CleanupItemResult {
  item_type: 'branch' | 'pr' | 'issue';
  identifier: string;
  action: 'deleted' | 'closed' | 'preserved' | 'failed';
  reason: string | null;
  error: string | null;
}

export interface CleanupExecuteRequest {
  owner: string;
  repo: string;
  project_id: string;
  branches_to_delete: string[];
  prs_to_close: number[];
  issues_to_delete: IssueToDelete[];
}

/** Payload from the confirm modal — the user's final selections after toggling. */
export interface CleanupConfirmPayload {
  branches_to_delete: string[];
  prs_to_close: number[];
  issues_to_delete: IssueToDelete[];
}

export interface CleanupExecuteResponse {
  operation_id: string;
  branches_deleted: number;
  branches_preserved: number;
  prs_closed: number;
  prs_preserved: number;
  issues_deleted: number;
  errors: CleanupItemResult[];
  results: CleanupItemResult[];
}

export interface CleanupAuditLogEntry {
  id: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  branches_deleted: number;
  branches_preserved: number;
  prs_closed: number;
  prs_preserved: number;
  errors_count: number;
  details: {
    results: CleanupItemResult[];
  } | null;
}

export interface CleanupHistoryResponse {
  operations: CleanupAuditLogEntry[];
  count: number;
}
