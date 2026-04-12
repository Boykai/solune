/**
 * Chore domain types.
 */

// ============ Chores Types (016-replace-housekeeping-chores) ============

export type ScheduleType = 'time' | 'count';
export type ChoreStatus = 'active' | 'paused';

export interface Chore {
  id: string;
  project_id: string;
  name: string;
  template_path: string;
  template_content: string;
  schedule_type: ScheduleType | null;
  schedule_value: number | null;
  status: ChoreStatus;
  last_triggered_at: string | null;
  last_triggered_count: number;
  current_issue_number: number | null;
  current_issue_node_id: string | null;
  pr_number: number | null;
  pr_url: string | null;
  tracking_issue_number: number | null;
  execution_count: number;
  ai_enhance_enabled: boolean;
  agent_pipeline_id: string;
  is_preset: boolean;
  preset_id: string;
  created_at: string;
  updated_at: string;
}

export interface ChoreCreate {
  name: string;
  template_content: string;
}

export interface ChoreTemplate {
  name: string;
  about: string;
  path: string;
  content: string;
}

export interface ChoreUpdate {
  schedule_type?: ScheduleType | null;
  schedule_value?: number | null;
  status?: ChoreStatus;
  ai_enhance_enabled?: boolean;
  agent_pipeline_id?: string;
}

export interface ChoreTriggerResult {
  chore_id: string;
  chore_name: string;
  triggered: boolean;
  issue_number: number | null;
  issue_url: string | null;
  skip_reason: string | null;
}

export interface EvaluateChoreTriggersResponse {
  evaluated: number;
  triggered: number;
  skipped: number;
  results: ChoreTriggerResult[];
}

export interface ChoreChatMessage {
  content: string;
  conversation_id?: string | null;
  ai_enhance?: boolean;
}

export interface ChoreChatResponse {
  message: string;
  conversation_id: string;
  template_ready: boolean;
  template_content: string | null;
  template_name: string | null;
}

// ── Inline Editing Types ──

export interface ChoreInlineUpdate {
  name?: string;
  template_content?: string;
  schedule_type?: ScheduleType | null;
  schedule_value?: number | null;
  ai_enhance_enabled?: boolean;
  agent_pipeline_id?: string;
  expected_sha?: string;
}

export interface ChoreInlineUpdateResponse {
  chore: Chore;
  pr_number: number | null;
  pr_url: string | null;
  pr_merged: boolean;
  merge_error: string | null;
}

export interface ChoreCreateWithConfirmation {
  name: string;
  template_content: string;
  ai_enhance_enabled: boolean;
  agent_pipeline_id: string;
  auto_merge: boolean;
}

export interface ChoreCreateResponse {
  chore: Chore;
  issue_number: number | null;
  pr_number: number | null;
  pr_url: string | null;
  pr_merged: boolean;
  merge_error: string | null;
}

// ── Featured Rituals Types ──

export interface FeaturedRitualCard {
  choreId: string;
  choreName: string;
  stat: string;
  statValue: number;
}

export interface FeaturedRituals {
  nextRun: FeaturedRitualCard | null;
  mostRecentlyRun: FeaturedRitualCard | null;
  mostRun: FeaturedRitualCard | null;
}

export interface ChoreEditState {
  original: Chore;
  current: Partial<ChoreInlineUpdate>;
  isDirty: boolean;
  fileSha: string | null;
}

export interface ChoreCounterData {
  choreId: string;
  remaining: number;
  totalThreshold: number;
  issuesSinceLastRun: number;
}
