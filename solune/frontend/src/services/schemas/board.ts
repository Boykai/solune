import { z } from 'zod';

const StatusColorSchema = z.enum(['GRAY', 'BLUE', 'GREEN', 'YELLOW', 'ORANGE', 'RED', 'PINK', 'PURPLE']);

const RateLimitInfoSchema = z
  .object({
    limit: z.number(),
    remaining: z.number(),
    reset_at: z.number(),
    used: z.number(),
  })
  .nullable()
  .optional();

const BoardLoadStateSchema = z.object({
  phase: z.enum(['interactive', 'backfilling_done', 'reconciling', 'complete']),
  active_columns_ready: z.boolean(),
  done_column_source: z.enum(['live', 'cached', 'pending']),
  warmed_by_selection: z.boolean(),
  pending_sections: z.array(z.string()).default([]),
  last_completed_at: z.string().nullable().optional(),
});

const DEFAULT_BOARD_LOAD_STATE = {
  phase: 'complete' as const,
  active_columns_ready: true,
  done_column_source: 'live' as const,
  warmed_by_selection: false,
  pending_sections: [],
  last_completed_at: null,
};

const BoardStatusOptionSchema = z.object({
  option_id: z.string(),
  name: z.string(),
  color: StatusColorSchema,
  description: z.string().optional(),
});

const BoardStatusFieldSchema = z.object({
  field_id: z.string(),
  options: z.array(BoardStatusOptionSchema),
});

const BoardProjectSchema = z.object({
  project_id: z.string(),
  name: z.string(),
  description: z.string().optional(),
  url: z.string(),
  owner_login: z.string(),
  status_field: BoardStatusFieldSchema,
});

const BoardRepositorySchema = z.object({
  owner: z.string(),
  name: z.string(),
});

const BoardAssigneeSchema = z.object({
  login: z.string(),
  avatar_url: z.string(),
});

const BoardCustomFieldValueSchema = z.object({
  name: z.string(),
  color: StatusColorSchema.optional(),
});

const LinkedPRSchema = z.object({
  pr_id: z.string(),
  number: z.number(),
  title: z.string(),
  state: z.enum(['open', 'closed', 'merged']),
  url: z.string(),
});

const BoardLabelSchema = z.object({
  id: z.string(),
  name: z.string(),
  color: z.string(),
});

const SubIssueSchema = z.object({
  id: z.string(),
  number: z.number(),
  title: z.string(),
  url: z.string(),
  state: z.string(),
  assigned_agent: z.string().nullable().optional(),
  assignees: z.array(BoardAssigneeSchema),
  linked_prs: z.array(LinkedPRSchema),
});

const BoardItemSchema = z.object({
  item_id: z.string(),
  content_id: z.string().optional(),
  content_type: z.enum(['issue', 'draft_issue', 'pull_request']),
  title: z.string(),
  number: z.number().optional(),
  repository: BoardRepositorySchema.optional(),
  url: z.string().optional(),
  body: z.string().optional(),
  status: z.string(),
  status_option_id: z.string(),
  assignees: z.array(BoardAssigneeSchema),
  priority: BoardCustomFieldValueSchema.optional(),
  size: BoardCustomFieldValueSchema.optional(),
  estimate: z.number().optional(),
  linked_prs: z.array(LinkedPRSchema),
  sub_issues: z.array(SubIssueSchema),
  labels: z.array(BoardLabelSchema),
  issue_type: z.string().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
  milestone: z.string().optional(),
  queued: z.boolean().optional(),
});

const BoardColumnSchema = z.object({
  status: BoardStatusOptionSchema,
  items: z.array(BoardItemSchema),
  item_count: z.number(),
  estimate_total: z.number(),
  next_cursor: z.string().nullable().optional(),
  has_more: z.boolean().optional(),
});

export const BoardDataResponseSchema = z.object({
  project: BoardProjectSchema,
  columns: z.array(BoardColumnSchema),
  load_state: BoardLoadStateSchema.optional().default(DEFAULT_BOARD_LOAD_STATE),
  rate_limit: RateLimitInfoSchema,
});
