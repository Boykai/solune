/**
 * Workflow domain types — agent assignment, workflow configuration, notifications.
 */

import type { ResolvedModelInfo } from './common';

// ============ Agent Assignment (004-agent-workflow-config-ui) ============

export type AgentSource = 'builtin' | 'repository';

export interface AgentAssignment {
  id: string; // UUID string
  slug: string; // Agent identifier
  display_name?: string | null;
  config?: Record<string, unknown> | null;
}

export interface AvailableAgent {
  slug: string;
  display_name: string;
  description?: string | null;
  avatar_url?: string | null;
  icon_name?: string | null;
  default_model_id?: string;
  default_model_name?: string;
  tools_count?: number | null;
  source: AgentSource;
}

export interface AgentPreset {
  id: string;
  label: string;
  description: string;
  mappings: Record<string, AgentAssignment[]>;
}

// ============ Workflow Result (T052) ============

export interface WorkflowResult {
  success: boolean;
  issue_id?: string;
  issue_number?: number;
  issue_url?: string;
  project_item_id?: string;
  current_status?: string;
  message: string;
  resolved_model?: ResolvedModelInfo | null;
}

export interface PipelineIssueLaunchRequest {
  issue_description: string;
  pipeline_id: string;
}

export interface WorkflowConfiguration {
  project_id: string;
  repository_owner: string;
  repository_name: string;
  copilot_assignee: string;
  review_assignee?: string;
  agent_mappings: Record<string, AgentAssignment[]>;
  status_backlog: string;
  status_ready: string;
  status_in_progress: string;
  status_in_review: string;
  enabled: boolean;
}

export interface AgentNotification {
  type: 'agent_assigned' | 'agent_completed';
  issue_number: number;
  agent_name: string;
  status: string;
  next_agent: string | null;
  timestamp: string;
}

export interface PipelineStateInfo {
  issue_number: number;
  project_id: string;
  status: string;
  agents: string[];
  current_agent_index: number;
  current_agent: string | null;
  completed_agents: string[];
  is_complete: boolean;
  started_at: string | null;
  error: string | null;
  queued: boolean;
}
