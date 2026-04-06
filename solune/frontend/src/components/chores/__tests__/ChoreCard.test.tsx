import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { ChoreCard } from '../ChoreCard';
import type { Chore } from '@/types';

vi.mock('@/hooks/useChores', () => ({
  useUpdateChore: () => ({ mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false }),
  useUndoableDeleteChore: () => ({ deleteChore: vi.fn() }),
  useTriggerChore: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock('@/hooks/useConfirmation', () => ({
  useConfirmation: () => ({ confirm: vi.fn().mockResolvedValue(false) }),
}));

vi.mock('../PipelineSelector', () => ({
  PipelineSelector: () => null,
  useProjectPipelineOptions: () => ({
    pipelines: [{ id: 'pipe-1', name: 'CI Pipeline', stage_count: 2 }],
  }),
}));

function createChore(overrides: Partial<Chore> = {}): Chore {
  return {
    id: 'chore-1',
    project_id: 'proj-1',
    name: 'Weekly Cleanup',
    template_path: '.github/ISSUE_TEMPLATE/cleanup.md',
    template_content: '# Cleanup',
    schedule_type: 'time',
    schedule_value: 7,
    status: 'active',
    last_triggered_at: null,
    last_triggered_count: 0,
    current_issue_number: null,
    current_issue_node_id: null,
    pr_number: null,
    pr_url: null,
    tracking_issue_number: null,
    execution_count: 0,
    ai_enhance_enabled: true,
    agent_pipeline_id: '',
    is_preset: false,
    preset_id: '',
    created_at: '2026-04-06T00:00:00Z',
    updated_at: '2026-04-06T00:00:00Z',
    ...overrides,
  };
}

describe('ChoreCard', () => {
  const originalRaf = window.requestAnimationFrame;
  const originalCancelRaf = window.cancelAnimationFrame;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    window.requestAnimationFrame = originalRaf;
    window.cancelAnimationFrame = originalCancelRaf;
  });

  it('cancels any pending animation frame on unmount', async () => {
    const user = userEvent.setup();
    const requestAnimationFrameSpy = vi.fn(() => 77);
    const cancelAnimationFrameSpy = vi.fn();
    window.requestAnimationFrame = requestAnimationFrameSpy;
    window.cancelAnimationFrame = cancelAnimationFrameSpy;

    const { unmount } = render(<ChoreCard chore={createChore()} projectId="proj-1" parentIssueCount={3} />);

    await user.click(screen.getByRole('button', { name: /agent pipeline/i }));
    window.dispatchEvent(new Event('resize'));
    unmount();

    expect(requestAnimationFrameSpy).toHaveBeenCalled();
    expect(cancelAnimationFrameSpy).toHaveBeenCalledWith(77);
  });
});
