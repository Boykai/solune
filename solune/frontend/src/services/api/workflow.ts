import type {
  AvailableAgent,
  WorkflowResult,
  WorkflowConfiguration,
  PipelineStateInfo,
} from '@/types';
import { request } from './client';
import { PipelineStateInfoSchema } from '@/services/schemas/pipeline';
import { validateResponse } from '@/services/schemas/validate';

export const workflowApi = {
  /**
   * Confirm an AI-generated issue recommendation.
   */
  confirmRecommendation(recommendationId: string): Promise<WorkflowResult> {
    return request<WorkflowResult>(`/workflow/recommendations/${recommendationId}/confirm`, {
      method: 'POST',
    });
  },

  /**
   * Reject an AI-generated issue recommendation.
   */
  rejectRecommendation(recommendationId: string): Promise<void> {
    return request<void>(`/workflow/recommendations/${recommendationId}/reject`, {
      method: 'POST',
    });
  },

  /**
   * Get the current workflow configuration.
   */
  getConfig(): Promise<WorkflowConfiguration> {
    return request<WorkflowConfiguration>('/workflow/config');
  },

  /**
   * Update workflow configuration.
   */
  updateConfig(config: WorkflowConfiguration): Promise<WorkflowConfiguration> {
    return request<WorkflowConfiguration>('/workflow/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  },

  /**
   * List available agents.
   */
  listAgents(): Promise<{ agents: AvailableAgent[] }> {
    return request<{ agents: AvailableAgent[] }>('/workflow/agents');
  },

  async getPipelineState(issueNumber: number): Promise<PipelineStateInfo> {
    const data = await request<PipelineStateInfo>(`/workflow/pipeline-states/${issueNumber}`);
    return validateResponse(PipelineStateInfoSchema, data, 'workflowApi.getPipelineState');
  },
};
