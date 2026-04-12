/**
 * Common types shared across multiple domains.
 */

// ============ User & Auth ============

export interface User {
  github_user_id: string;
  github_username: string;
  github_avatar_url?: string;
  selected_project_id?: string;
}

export interface AuthResponse {
  user: User;
  message: string;
}

// ============ API Error ============

export interface APIError {
  error: string;
  details?: Record<string, unknown>;
}

// ============ Pagination ============

export interface PaginatedResponse<T> {
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
  total_count: number | null;
}

export interface RateLimitInfo {
  limit: number;
  remaining: number;
  reset_at: number;
  used: number;
}

export type RefreshErrorType = 'rate_limit' | 'network' | 'auth' | 'server' | 'unknown';

export interface RefreshError {
  type: RefreshErrorType;
  message: string;
  rateLimitInfo?: RateLimitInfo;
  retryAfter?: Date;
}

// ============ Status Color (shared by Board & Navigation) ============

export type StatusColor =
  | 'GRAY'
  | 'BLUE'
  | 'GREEN'
  | 'YELLOW'
  | 'ORANGE'
  | 'RED'
  | 'PINK'
  | 'PURPLE';

// ============ Resolved Model Info ============

/**
 * Metadata describing how a concrete model was chosen for a chat or pipeline action.
 *
 * `model_id`, `model_name`, and `source` are typically present when resolution succeeds.
 * `guidance` is typically present when Auto resolution fails and the UI should steer the
 * user toward a manual model selection.
 */
export interface ResolvedModelInfo {
  selection_mode: 'auto' | 'explicit';
  resolution_status: 'resolved' | 'failed';
  model_id?: string | null;
  model_name?: string | null;
  source?: 'pipeline_override' | 'agent_default' | 'user_default' | 'provider_default' | 'unknown';
  guidance?: string | null;
}

// ============ Solune UI Redesign Types (025) ============

export interface NavRoute {
  path: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

export interface SidebarState {
  isCollapsed: boolean;
}

export interface RecentInteraction {
  item_id: string;
  title: string;
  number?: number;
  repository?: {
    owner: string;
    name: string;
  };
  updatedAt: string;
  status: string;
  statusColor: StatusColor;
}

export interface Notification {
  id: string;
  type: 'agent' | 'chore' | 'pipeline';
  title: string;
  timestamp: string;
  read: boolean;
  source?: string;
}

// ============ Onboarding Tour & Help Types (042) ============

export type TourStepPlacement = 'top' | 'bottom' | 'left' | 'right';

export interface TourStep {
  id: number;
  targetSelector: string | null;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  placement: TourStepPlacement;
}

export type FaqCategory = 'getting-started' | 'agents-pipelines' | 'chat-voice' | 'settings-integration';

export interface FaqEntry {
  id: string;
  question: string;
  answer: string;
  category: FaqCategory;
}
