/**
 * Chat domain types — messages, proposals, plans, mentions, file uploads.
 */

import type { ResolvedModelInfo } from './common';
import type { PipelineConfigSummary } from './pipeline';

// ============ Enums ============

export type SenderType = 'user' | 'assistant' | 'system';

export type ActionType = 'task_create' | 'status_update' | 'project_select' | 'issue_create' | 'pipeline_launch' | 'plan_create' | 'app_import' | 'app_build' | 'app_iterate';

export type ProposalStatus = 'pending' | 'confirmed' | 'edited' | 'cancelled';

export type RecommendationStatus = 'pending' | 'confirmed' | 'rejected';

export type MessageStatus = 'pending' | 'sent' | 'failed';

// ============ Action Data ============

export interface TaskCreateActionData {
  proposal_id: string;
  task_id?: string;
  status: ProposalStatus;
  proposed_title?: string;
  proposed_description?: string;
}

export interface StatusUpdateActionData {
  task_id: string;
  new_status?: string;
  confirmed?: boolean;
  proposal_id?: string;
  task_title?: string;
  current_status?: string;
  target_status?: string;
  status_option_id?: string;
  status_field_id?: string;
  status?: string;
}

export interface ProjectSelectActionData {
  project_id: string;
  project_name: string;
}

export interface PipelineLaunchActionData {
  pipeline_id: string;
  preset: string;
  stages: string[];
}

// ============ Plan Mode Types ============

export type PlanStatus = 'draft' | 'approved' | 'completed' | 'failed';
export type ThinkingPhase = 'researching' | 'planning' | 'refining' | 'reasoning' | 'tool_start';
export type StepApprovalStatus = 'pending' | 'approved' | 'rejected';

export interface ThinkingEvent {
  phase: ThinkingPhase;
  detail: string;
}

export interface PlanStep {
  step_id: string;
  position: number;
  title: string;
  description: string;
  dependencies: string[];
  approval_status?: StepApprovalStatus;
  issue_number?: number;
  issue_url?: string;
}

export interface Plan {
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
  steps: PlanStep[];
  created_at: string;
  updated_at: string;
}

export interface PlanVersion {
  version_id: string;
  plan_id: string;
  version: number;
  title: string;
  summary: string;
  steps_json: string;
  created_at: string;
}

export interface PlanHistoryResponse {
  plan_id: string;
  current_version: number;
  versions: PlanVersion[];
}

export interface PlanCreateActionData {
  plan_id: string;
  title: string;
  summary: string;
  status: PlanStatus;
  project_id: string;
  project_name: string;
  repo_owner: string;
  repo_name: string;
  steps: PlanStep[];
}

export interface PlanApprovalResponse {
  plan_id: string;
  status: PlanStatus;
  parent_issue_number?: number;
  parent_issue_url?: string;
  steps: PlanStep[];
}

export interface PlanExitResponse {
  message: string;
  plan_id: string;
  plan_status: PlanStatus;
}

// ============ Plan v2 Request/Response Types ============

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

export interface StepFeedbackRequest {
  feedback_type: 'comment' | 'approve' | 'reject';
  content: string;
}

export interface StepFeedbackResponse {
  step_id: string;
  feedback_type: string;
  status: 'accepted' | 'queued';
}

export interface DependencyGraphNode {
  step_id: string;
  title: string;
  position: number;
  approval_status?: StepApprovalStatus;
  dependencies: string[];
}

export interface DependencyGraphEdge {
  from: string;
  to: string;
}

// ============ Issue Recommendation ============

export type IssuePriority = 'P0' | 'P1' | 'P2' | 'P3';

export type IssueSize = 'XS' | 'S' | 'M' | 'L' | 'XL';

export type IssueLabel =
  | 'feature'
  | 'bug'
  | 'enhancement'
  | 'refactor'
  | 'documentation'
  | 'testing'
  | 'infrastructure'
  | 'frontend'
  | 'backend'
  | 'database'
  | 'api'
  | 'ai-generated'
  | 'good first issue'
  | 'help wanted'
  | 'security'
  | 'performance'
  | 'accessibility'
  | 'ux';

export interface IssueMetadata {
  priority: IssuePriority;
  size: IssueSize;
  estimate_hours: number;
  start_date: string;
  target_date: string;
  labels: IssueLabel[];
  assignees?: string[];
  milestone?: string | null;
  branch?: string | null;
}

export interface RepositoryMetadata {
  repo_key: string;
  labels: Array<{ name: string; color: string; description: string }>;
  branches: Array<{ name: string; protected: boolean }>;
  milestones: Array<{ number: number; title: string; due_on: string | null; state: string }>;
  collaborators: Array<{ login: string; avatar_url: string }>;
  fetched_at: string;
  is_stale: boolean;
  source: 'fresh' | 'cache' | 'fallback';
}

export interface IssueRecommendation {
  recommendation_id: string;
  session_id: string;
  original_input: string;
  title: string;
  user_story: string;
  ui_ux_description: string;
  functional_requirements: string[];
  metadata: IssueMetadata;
  status: RecommendationStatus;
  created_at: string;
  confirmed_at?: string;
}

export interface IssueCreateActionData {
  recommendation_id: string;
  proposed_title: string;
  user_story: string;
  ui_ux_description: string;
  functional_requirements: string[];
  metadata?: IssueMetadata;
  status: RecommendationStatus;
}

export type ActionData =
  | TaskCreateActionData
  | StatusUpdateActionData
  | ProjectSelectActionData
  | IssueCreateActionData
  | PipelineLaunchActionData
  | PlanCreateActionData;

// ============ Chat Messages ============

export interface ChatMessage {
  message_id: string;
  session_id: string;
  sender_type: SenderType;
  content: string;
  action_type?: ActionType;
  action_data?: ActionData;
  timestamp: string;
  status?: MessageStatus;
  resolved_model?: ResolvedModelInfo | null;
  conversation_id?: string | null;
}

export interface ChatMessageRequest {
  content: string;
  ai_enhance?: boolean;
  file_urls?: string[];
  pipeline_id?: string;
  conversation_id?: string;
}

export interface ChatMessagesResponse {
  messages: ChatMessage[];
}

// ============ @Mention Types ============

/** Represents a single @mention reference within the chat input. */
export interface MentionToken {
  pipelineId: string;
  pipelineName: string;
  isValid: boolean;
  position: number;
}

/** Internal state managed by the useMentionAutocomplete hook. */
export interface MentionInputState {
  isAutocompleteOpen: boolean;
  filterQuery: string;
  highlightedIndex: number;
  mentionTriggerOffset: number | null;
  activePipelineId: string | null;
  activePipelineName: string | null;
  tokens: MentionToken[];
  hasInvalidTokens: boolean;
}

/** A pipeline matching the current filter query for autocomplete display. */
export interface MentionFilterResult {
  pipeline: PipelineConfigSummary;
  matchIndices: [number, number][];
}

// ============ Chat Enhancement Types ============

/** State of a file pending upload or already uploaded */
export interface FileAttachment {
  id: string;
  file: File;
  filename: string;
  fileSize: number;
  contentType: string;
  status: 'pending' | 'uploading' | 'uploaded' | 'error';
  progress: number;
  fileUrl: string | null;
  error: string | null;
}

/** Voice input recording state */
export interface VoiceInputState {
  isSupported: boolean;
  isRecording: boolean;
  isProcessing: boolean;
  interimTranscript: string;
  finalTranscript: string;
  error: string | null;
}

/** AI Enhance toggle state */
export interface ChatPreferences {
  aiEnhance: boolean;
}

/** File upload validation constants */
export const FILE_VALIDATION = {
  maxFileSize: 10 * 1024 * 1024, // 10 MB
  maxFilesPerMessage: 5,
  allowedImageTypes: ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'],
  allowedDocTypes: ['.pdf', '.txt', '.md', '.csv', '.json', '.yaml', '.yml', '.vtt', '.srt'],
  allowedArchiveTypes: ['.zip'],
  blockedTypes: ['.exe', '.sh', '.bat', '.cmd', '.js', '.py', '.rb'],
} as const;

export const ALLOWED_TYPES = [
  ...FILE_VALIDATION.allowedImageTypes,
  ...FILE_VALIDATION.allowedDocTypes,
  ...FILE_VALIDATION.allowedArchiveTypes,
];

/** File upload response from backend */
export interface FileUploadResponse {
  filename: string;
  file_url: string;
  file_size: number;
  content_type: string;
}

/** File upload error response from backend */
export interface FileUploadError {
  filename: string;
  error: string;
  error_code: string;
}

// ============ Conversations ============

export interface Conversation {
  conversation_id: string;
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationsListResponse {
  conversations: Conversation[];
}

// ============ AI Task Proposals ============

export interface AITaskProposal {
  proposal_id: string;
  session_id: string;
  original_input: string;
  proposed_title: string;
  proposed_description: string;
  status: ProposalStatus;
  edited_title?: string;
  edited_description?: string;
  created_at: string;
  expires_at: string;
  pipeline_name?: string;
  pipeline_source?: string;
}

export interface ProposalConfirmRequest {
  edited_title?: string;
  edited_description?: string;
}

// ============ Status Change Proposal ============

export interface StatusChangeProposal {
  proposal_id: string;
  task_id: string;
  task_title: string;
  current_status: string;
  target_status: string;
  status_option_id: string;
  status_field_id: string;
  status: string;
}
