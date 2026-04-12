/**
 * Pipeline domain types — pipeline configuration, stages, agents, models.
 */

// ============ Pipeline Types ============

export interface PipelineAgentNode {
  id: string;
  agent_slug: string;
  agent_display_name: string;
  model_id: string;
  model_name: string;
  tool_ids: string[];
  tool_count: number;
  config: Record<string, unknown>;
}

export interface ExecutionGroup {
  id: string;
  order: number;
  execution_mode: 'sequential' | 'parallel';
  agents: PipelineAgentNode[];
}

export interface PipelineStage {
  id: string;
  name: string;
  order: number;
  /** Ordered execution groups within this stage. */
  groups?: ExecutionGroup[];
  agents: PipelineAgentNode[];
  execution_mode?: 'sequential' | 'parallel';
}

export interface PipelineConfig {
  id: string;
  project_id: string;
  name: string;
  description: string;
  stages: PipelineStage[];
  is_preset: boolean;
  preset_id: string;
  created_at: string;
  updated_at: string;
  auto_merge?: boolean;
}

export interface PipelineConfigSummary {
  id: string;
  name: string;
  description: string;
  stage_count: number;
  agent_count: number;
  total_tool_count: number;
  is_preset: boolean;
  preset_id: string;
  stages: PipelineStage[];
  updated_at: string;
}

export interface PipelineConfigListResponse {
  pipelines: PipelineConfigSummary[];
  total: number;
}

export interface PipelineConfigCreate {
  name: string;
  description?: string;
  stages: PipelineStage[];
}

export interface PipelineConfigUpdate {
  name?: string;
  description?: string;
  stages?: PipelineStage[];
}

export interface AIModel {
  id: string;
  name: string;
  provider: string;
  context_window_size?: number;
  cost_tier?: 'economy' | 'standard' | 'premium';
  capability_category?: string;
  supported_reasoning_efforts?: string[];
  default_reasoning_effort?: string | null;
  reasoning_effort?: string;
}

export interface ModelGroup {
  provider: string;
  models: AIModel[];
}

export type PipelineBoardState = 'empty' | 'creating' | 'editing';

export interface PipelineModelOverride {
  mode: 'auto' | 'specific' | 'mixed';
  modelId: string;
  modelName: string;
  reasoningEffort?: string;
}

export interface PipelineValidationErrors {
  name?: string;
  stages?: string;
  [key: string]: string | undefined;
}

export interface ProjectPipelineAssignment {
  project_id: string;
  pipeline_id: string;
}

export interface PresetPipelineDefinition {
  presetId: string;
  name: string;
  description: string;
  stages: PipelineStage[];
}

export interface FlowGraphNode {
  id: string;
  label: string;
  agentCount: number;
  x: number;
  y: number;
}

export interface PresetSeedResult {
  seeded: string[];
  skipped: string[];
  total: number;
}
