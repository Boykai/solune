/**
 * usePlan hook — manages plan mode state, approve/exit mutations,
 * step CRUD, versioning, and feedback.
 */

import { useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { chatApi } from '@/services/api';
import type {
  Plan,
  PlanApprovalResponse,
  StepApprovalRequest,
  StepCreateRequest,
  StepFeedbackRequest,
  StepUpdateRequest,
  ThinkingPhase,
} from '@/types';

/**
 * usePlanHistory — fetches version history for a plan.
 *
 * Extracted as a standalone hook to comply with the Rules of Hooks
 * (hooks must be called unconditionally at the top level of a
 * component or custom hook).
 */
export function usePlanHistory(planId: string | undefined) {
  return useQuery({
    queryKey: ['planHistory', planId],
    queryFn: () => (planId ? chatApi.getPlanHistory(planId) : []),
    enabled: !!planId,
  });
}

export function usePlan() {
  const queryClient = useQueryClient();
  const [activePlan, setActivePlan] = useState<Plan | null>(null);
  const [isPlanMode, setIsPlanMode] = useState(false);
  const [thinkingPhase, setThinkingPhase] = useState<ThinkingPhase | null>(null);
  const [thinkingDetail, setThinkingDetail] = useState<string>('');

  const planQuery = useQuery({
    queryKey: ['plan', activePlan?.plan_id],
    queryFn: () => (activePlan?.plan_id ? chatApi.getPlan(activePlan.plan_id) : null),
    enabled: !!activePlan?.plan_id,
  });

  const approveMutation = useMutation({
    mutationFn: (planId: string) => chatApi.approvePlan(planId),
    onSuccess: (data: PlanApprovalResponse) => {
      if (activePlan) {
        setActivePlan({
          ...activePlan,
          status: data.status,
          parent_issue_number: data.parent_issue_number,
          parent_issue_url: data.parent_issue_url,
          steps: data.steps.map((s) => ({
            ...s,
            dependencies: s.dependencies ?? [],
          })),
        });
      }
      queryClient.invalidateQueries({ queryKey: ['plan'] });
    },
  });

  const exitMutation = useMutation({
    mutationFn: (planId: string) => chatApi.exitPlanMode(planId),
    onSuccess: () => {
      setActivePlan(null);
      setIsPlanMode(false);
      setThinkingPhase(null);
      setThinkingDetail('');
      queryClient.invalidateQueries({ queryKey: ['plan'] });
    },
  });

  // ============ Plan v2 Mutations ============

  const addStepMutation = useMutation({
    mutationFn: ({ planId, data }: { planId: string; data: StepCreateRequest }) =>
      chatApi.addStep(planId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plan'] });
    },
  });

  const updateStepMutation = useMutation({
    mutationFn: ({ planId, stepId, data }: { planId: string; stepId: string; data: StepUpdateRequest }) =>
      chatApi.updateStep(planId, stepId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plan'] });
    },
  });

  const deleteStepMutation = useMutation({
    mutationFn: ({ planId, stepId }: { planId: string; stepId: string }) =>
      chatApi.deleteStep(planId, stepId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plan'] });
    },
  });

  const reorderStepsMutation = useMutation({
    mutationFn: ({ planId, stepIds }: { planId: string; stepIds: string[] }) =>
      chatApi.reorderSteps(planId, { step_ids: stepIds }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plan'] });
    },
  });

  const approveStepMutation = useMutation({
    mutationFn: ({ planId, stepId, data }: { planId: string; stepId: string; data: StepApprovalRequest }) =>
      chatApi.approveStep(planId, stepId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plan'] });
    },
  });

  const submitFeedbackMutation = useMutation({
    mutationFn: ({ planId, stepId, data }: { planId: string; stepId: string; data: StepFeedbackRequest }) =>
      chatApi.submitStepFeedback(planId, stepId, data),
  });

  const enterPlanMode = useCallback((plan: Plan) => {
    setActivePlan(plan);
    setIsPlanMode(true);
  }, []);

  const clearThinking = useCallback(() => {
    setThinkingPhase(null);
    setThinkingDetail('');
  }, []);

  return {
    activePlan,
    setActivePlan,
    isPlanMode,
    setIsPlanMode,
    thinkingPhase,
    setThinkingPhase,
    thinkingDetail,
    setThinkingDetail,
    clearThinking,
    enterPlanMode,
    approveMutation,
    exitMutation,
    planQuery,
    // v2
    addStepMutation,
    updateStepMutation,
    deleteStepMutation,
    reorderStepsMutation,
    approveStepMutation,
    submitFeedbackMutation,
  };
}
