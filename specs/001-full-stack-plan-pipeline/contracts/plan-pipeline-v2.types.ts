/**
 * Frontend TypeScript type extensions for Plan Pipeline v2.
 *
 * These types extend the existing Plan/PlanStep types in
 * solune/frontend/src/types/index.ts with versioning, step CRUD,
 * feedback, and enhanced SSE event support.
 */

// ─── Extended Plan Types ────────────────────────────────────────────

/** Per-step approval status (new) */
export type StepApprovalStatus = 'pending' | 'approved' | 'rejected';

/** Extended PlanStep with approval_status */
export interface PlanStepV2 {
  step_id: string;
  plan_id: string;
  position: number;
  title: string;
  description: string;
  dependencies: string[];
  approval_status: StepApprovalStatus;
  issue_number?: number;
  issue_url?: string;
}

/** Extended Plan with version field */
export interface PlanV2 {
  plan_id: string;
  session_id: string;
  title: string;
  summary: string;
  status: PlanStatus;
  version: number;
  project_id: string;
  project_name: string;
  repo_owner: string;
  repo_name: string;
  parent_issue_number?: number;
  parent_issue_url?: string;
  steps: PlanStepV2[];
  created_at: string;
  updated_at: string;
}

// ─── Plan Versioning Types ──────────────────────────────────────────

export interface PlanVersion {
  version_id: string;
  plan_id: string;
  version: number;
  title: string;
  summary: string;
  steps: PlanStepV2[];
  created_at: string;
}

/** The history endpoint returns a wrapper with plan_id, current_version, and versions. */
export interface PlanHistoryResponse {
  plan_id: string;
  current_version: number;
  versions: PlanVersion[];
}

// ─── Step CRUD Types ────────────────────────────────────────────────

export interface StepCreateRequest {
  title: string;
  description: string;
  dependencies?: string[];
  position?: number;
}

export interface StepUpdateRequest {
  title?: string;
  description?: string;
  dependencies?: string[];
}

export interface StepReorderRequest {
  step_ids: string[];
}

export interface StepApprovalRequest {
  approval_status: StepApprovalStatus;
}

// ─── Step Feedback Types ────────────────────────────────────────────

export type FeedbackType = 'comment' | 'approve' | 'reject';

export interface StepFeedbackRequest {
  feedback_type: FeedbackType;
  content: string;
}

export interface StepFeedbackResponse {
  step_id: string;
  feedback_type: string;
  status: 'accepted' | 'queued';
}

// ─── Enhanced SSE Event Types ───────────────────────────────────────

/** Extended thinking phases (v2) */
export type ThinkingPhaseV2 =
  | 'researching'
  | 'planning'
  | 'refining'
  | 'reasoning';

/** SDK reasoning delta event */
export interface ReasoningEvent {
  content: string;
}

/** Tool execution start event */
export interface ToolStartEvent {
  tool: string;
  args: Record<string, unknown>;
}

/** Pipeline stage events */
export interface StageEvent {
  stage: string;
  agent: string;
  result?: Record<string, unknown>;
  error?: string;
}

/** Plan diff event (emitted after save_plan via post-hook) */
export interface PlanDiffEvent {
  plan_id: string;
  from_version: number;
  to_version: number;
}

/** Union type for all v2 SSE events */
export type PlanSSEEvent =
  | { event: 'token'; data: { content: string } }
  | { event: 'thinking'; data: { phase: ThinkingPhaseV2; detail: string } }
  | { event: 'reasoning'; data: ReasoningEvent }
  | { event: 'tool_start'; data: ToolStartEvent }
  | { event: 'tool_call'; data: { tool: string; args: Record<string, unknown> } }
  | { event: 'tool_result'; data: { action_type: string; action_data: Record<string, unknown> } }
  | { event: 'stage_started'; data: StageEvent }
  | { event: 'stage_completed'; data: StageEvent }
  | { event: 'stage_failed'; data: StageEvent }
  | { event: 'plan_diff'; data: PlanDiffEvent }
  | { event: 'done'; data: { message_id: string; sender_type: string } }
  | { event: 'error'; data: { error: string } };

// ─── Dependency Graph Types ─────────────────────────────────────────

export interface DependencyNode {
  step_id: string;
  title: string;
  position: number;
  approval_status: StepApprovalStatus;
  dependencies: string[];
}

export interface DependencyEdge {
  from: string;
  to: string;
}

export interface DependencyGraph {
  nodes: DependencyNode[];
  edges: DependencyEdge[];
}

// ─── Re-export existing types for compatibility ─────────────────────

export type { PlanStatus } from './index';
