/**
 * Tests for usePlan hook — plan mode state management.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

vi.mock('@/services/api', () => ({
  chatApi: {
    getPlan: vi.fn().mockResolvedValue(null),
    approvePlan: vi.fn(),
    exitPlanMode: vi.fn(),
  },
}));

import * as api from '@/services/api';
import { usePlan } from './usePlan';
import type { Plan, PlanApprovalResponse } from '@/types';

const mockChatApi = api.chatApi as unknown as {
  getPlan: ReturnType<typeof vi.fn>;
  approvePlan: ReturnType<typeof vi.fn>;
  exitPlanMode: ReturnType<typeof vi.fn>;
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function createPlan(overrides: Partial<Plan> = {}): Plan {
  return {
    plan_id: 'plan-1',
    session_id: 'sess-1',
    title: 'Test Plan',
    summary: 'A test plan',
    status: 'draft',
    version: 1,
    project_id: 'proj-1',
    project_name: 'My Project',
    repo_owner: 'octocat',
    repo_name: 'hello-world',
    steps: [],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('usePlan', () => {
  beforeEach(() => vi.clearAllMocks());

  it('starts with null active plan and plan mode off', () => {
    const { result } = renderHook(() => usePlan(), { wrapper: createWrapper() });
    expect(result.current.activePlan).toBeNull();
    expect(result.current.isPlanMode).toBe(false);
    expect(result.current.thinkingPhase).toBeNull();
    expect(result.current.thinkingDetail).toBe('');
  });

  it('enterPlanMode sets activePlan and isPlanMode', () => {
    const { result } = renderHook(() => usePlan(), { wrapper: createWrapper() });
    const plan = createPlan();

    act(() => {
      result.current.enterPlanMode(plan);
    });

    expect(result.current.activePlan).toEqual(plan);
    expect(result.current.isPlanMode).toBe(true);
  });

  it('setThinkingPhase and clearThinking manage thinking state', () => {
    const { result } = renderHook(() => usePlan(), { wrapper: createWrapper() });

    act(() => {
      result.current.setThinkingPhase('researching');
      result.current.setThinkingDetail('Analyzing project…');
    });

    expect(result.current.thinkingPhase).toBe('researching');
    expect(result.current.thinkingDetail).toBe('Analyzing project…');

    act(() => {
      result.current.clearThinking();
    });

    expect(result.current.thinkingPhase).toBeNull();
    expect(result.current.thinkingDetail).toBe('');
  });

  it('approveMutation calls approvePlan and updates active plan on success', async () => {
    const approvalResponse: PlanApprovalResponse = {
      plan_id: 'plan-1',
      status: 'completed',
      parent_issue_number: 42,
      parent_issue_url: 'https://github.com/octocat/hello-world/issues/42',
      steps: [
        {
          step_id: 's-1',
          position: 0,
          title: 'Step 1',
          description: 'D',
          dependencies: [],
          issue_number: 43,
          issue_url: 'https://github.com/octocat/hello-world/issues/43',
        },
      ],
    };
    mockChatApi.approvePlan.mockResolvedValue(approvalResponse);

    const { result } = renderHook(() => usePlan(), { wrapper: createWrapper() });

    // Enter plan mode first
    act(() => {
      result.current.enterPlanMode(createPlan());
    });

    // Approve the plan
    act(() => {
      result.current.approveMutation.mutate('plan-1');
    });

    await waitFor(() => {
      expect(result.current.approveMutation.isSuccess).toBe(true);
    });

    expect(mockChatApi.approvePlan).toHaveBeenCalledWith('plan-1');
    expect(result.current.activePlan?.status).toBe('completed');
    expect(result.current.activePlan?.parent_issue_number).toBe(42);
  });

  it('exitMutation calls exitPlanMode and resets all state', async () => {
    mockChatApi.exitPlanMode.mockResolvedValue({
      message: 'Plan mode deactivated',
      plan_id: 'plan-1',
      plan_status: 'draft',
    });

    const { result } = renderHook(() => usePlan(), { wrapper: createWrapper() });

    // Enter plan mode first
    act(() => {
      result.current.enterPlanMode(createPlan());
      result.current.setThinkingPhase('planning');
      result.current.setThinkingDetail('Working…');
    });

    expect(result.current.isPlanMode).toBe(true);

    // Exit plan mode
    act(() => {
      result.current.exitMutation.mutate('plan-1');
    });

    await waitFor(() => {
      expect(result.current.exitMutation.isSuccess).toBe(true);
    });

    expect(mockChatApi.exitPlanMode).toHaveBeenCalledWith('plan-1');
    expect(result.current.activePlan).toBeNull();
    expect(result.current.isPlanMode).toBe(false);
    expect(result.current.thinkingPhase).toBeNull();
    expect(result.current.thinkingDetail).toBe('');
  });
});
