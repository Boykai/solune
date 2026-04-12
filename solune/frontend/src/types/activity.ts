/**
 * Activity event types (054-activity-audit-trail).
 */

export interface ActivityEvent {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  project_id: string;
  actor: string;
  action: string;
  summary: string;
  detail?: Record<string, unknown>;
  created_at: string;
}

export interface ActivityStats {
  total_count: number;
  today_count: number;
  by_type: Record<string, number>;
  last_event_at: string | null;
}
