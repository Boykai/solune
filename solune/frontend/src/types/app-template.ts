/** App template and build progress types for the Autonomous App Builder. */

// ── Template Types ──────────────────────────────────────────────────────

export type AppCategory = 'saas' | 'api' | 'cli' | 'dashboard';
export type ScaffoldType = 'skeleton' | 'starter';
export type IaCTarget = 'none' | 'azure' | 'aws' | 'docker';
export type Difficulty = 'S' | 'M' | 'L' | 'XL';

export interface TemplateFile {
  source: string;
  target: string;
  variables: string[];
}

export interface AppTemplateSummary {
  id: string;
  name: string;
  description: string;
  category: AppCategory;
  difficulty: Difficulty;
  tech_stack: string[];
  scaffold_type: ScaffoldType;
  iac_target: IaCTarget;
}

export interface AppTemplate extends AppTemplateSummary {
  files: TemplateFile[];
  recommended_preset_id: string;
}

// ── Build Progress Types ────────────────────────────────────────────────

export type BuildPhase =
  | 'scaffolding'
  | 'configuring'
  | 'issuing'
  | 'building'
  | 'deploying_prep'
  | 'complete'
  | 'failed';

export type BuildMilestone = 'scaffolded' | 'working' | 'review' | 'complete';

export interface BuildProgressPayload {
  type: 'build_progress';
  app_name: string;
  phase: BuildPhase;
  agent_name: string | null;
  detail: string;
  pct_complete: number;
  updated_at: string;
}

export interface BuildMilestonePayload {
  type: 'build_milestone';
  app_name: string;
  milestone: BuildMilestone;
  message: string;
  updated_at: string;
}

export interface BuildCompletePayload {
  type: 'build_complete';
  app_name: string;
  message: string;
  links: {
    app_url?: string;
    repo_url?: string;
    project_url?: string | null;
    issue_url?: string;
  };
  updated_at: string;
}

export interface BuildFailedPayload {
  type: 'build_failed';
  app_name: string;
  phase: string;
  message: string;
  updated_at: string;
}

// ── Import Types ────────────────────────────────────────────────────────

export interface ImportAppRequest {
  url: string;
  pipeline_id?: string | null;
  create_project?: boolean;
}

export interface ImportAppResponse {
  app: import('./apps').App;
  message: string;
  project_url?: string | null;
}

// ── Build / Iterate Types ───────────────────────────────────────────────

export interface BuildAppRequest {
  template_id: string;
  description?: string;
  difficulty_override?: Difficulty | null;
  context_variables?: Record<string, string>;
  create_project?: boolean;
}

export interface BuildAppResponse {
  app_name: string;
  pipeline_run_id?: number | null;
  issue_url?: string | null;
  project_url?: string | null;
  message: string;
}

export interface IterateRequest {
  change_description: string;
}

export interface IterateResponse {
  issue_url?: string | null;
  pipeline_run_id?: number | null;
  message: string;
}
