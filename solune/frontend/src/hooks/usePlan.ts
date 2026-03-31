/**
 * usePlan hook — manages plan mode state, approve/exit mutations.
 */

import { useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { chatApi } from '@/services/api';
import type { Plan, PlanApprovalResponse, ThinkingPhase } from '@/types';

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
  };
}
