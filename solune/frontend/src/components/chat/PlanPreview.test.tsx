/**
 * Tests for PlanPreview — rich plan display card for the /plan planning mode.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, userEvent } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';
import { PlanPreview } from './PlanPreview';
import type { PlanCreateActionData, PlanApprovalResponse } from '@/types';

function createPlan(overrides: Partial<PlanCreateActionData> = {}): PlanCreateActionData {
  return {
    plan_id: 'plan-1',
    title: 'Add Auth Feature',
    summary: 'Implement OAuth login for the application.',
    status: 'draft',
    project_id: 'proj-1',
    project_name: 'My Project',
    repo_owner: 'octocat',
    repo_name: 'hello-world',
    steps: [
      {
        step_id: 's-1',
        position: 0,
        title: 'Setup OAuth provider',
        description: 'Configure OAuth with GitHub.',
        dependencies: [],
      },
      {
        step_id: 's-2',
        position: 1,
        title: 'Add login endpoint',
        description: 'Create POST /login route.',
        dependencies: ['s-1'],
      },
    ],
    ...overrides,
  };
}

describe('PlanPreview', () => {
  it('renders plan title and summary', () => {
    render(<PlanPreview plan={createPlan()} />);
    expect(screen.getByText('Add Auth Feature')).toBeInTheDocument();
    expect(screen.getByText('Implement OAuth login for the application.')).toBeInTheDocument();
  });

  it('renders Plan Preview header', () => {
    render(<PlanPreview plan={createPlan()} />);
    expect(screen.getByText('Plan Preview')).toBeInTheDocument();
  });

  it('renders repo badge', () => {
    render(<PlanPreview plan={createPlan()} />);
    expect(screen.getByText('octocat/hello-world')).toBeInTheDocument();
  });

  it('renders status badge for draft', () => {
    render(<PlanPreview plan={createPlan({ status: 'draft' })} />);
    expect(screen.getByText('Draft')).toBeInTheDocument();
  });

  it('renders step count', () => {
    render(<PlanPreview plan={createPlan()} />);
    expect(screen.getByText('Steps (2)')).toBeInTheDocument();
  });

  it('renders step titles', () => {
    render(<PlanPreview plan={createPlan()} />);
    expect(screen.getByText('Setup OAuth provider')).toBeInTheDocument();
    expect(screen.getByText('Add login endpoint')).toBeInTheDocument();
  });

  it('renders step position numbers', () => {
    render(<PlanPreview plan={createPlan()} />);
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders dependency annotation', () => {
    render(<PlanPreview plan={createPlan()} />);
    expect(screen.getByText(/depends on:.*Step 1/)).toBeInTheDocument();
  });

  it('renders Approve & Create Issues button for draft plan', () => {
    const onApprove = vi.fn().mockResolvedValue({});
    render(<PlanPreview plan={createPlan()} onApprove={onApprove} />);
    expect(screen.getByRole('button', { name: /Approve & Create Issues/ })).toBeInTheDocument();
  });

  it('renders Request Changes button for draft plan', () => {
    const onRequestChanges = vi.fn();
    render(<PlanPreview plan={createPlan()} onRequestChanges={onRequestChanges} />);
    expect(screen.getByRole('button', { name: 'Request Changes' })).toBeInTheDocument();
  });

  it('calls onApprove when Approve button is clicked', async () => {
    const onApprove = vi.fn().mockResolvedValue({});
    render(<PlanPreview plan={createPlan()} onApprove={onApprove} />);
    await userEvent.setup().click(screen.getByRole('button', { name: /Approve & Create Issues/ }));
    expect(onApprove).toHaveBeenCalledWith('plan-1');
  });

  it('calls onRequestChanges when Request Changes is clicked', async () => {
    const onRequestChanges = vi.fn();
    render(<PlanPreview plan={createPlan()} onRequestChanges={onRequestChanges} />);
    await userEvent.setup().click(screen.getByRole('button', { name: 'Request Changes' }));
    expect(onRequestChanges).toHaveBeenCalledTimes(1);
  });

  it('shows spinner when isApproving is true', () => {
    const onApprove = vi.fn().mockResolvedValue({});
    render(<PlanPreview plan={createPlan()} onApprove={onApprove} isApproving />);
    expect(screen.getByRole('button', { name: /Creating Issues/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Creating Issues/ })).toBeDisabled();
  });

  it('shows error message when approveError is set', () => {
    render(<PlanPreview plan={createPlan()} approveError="GitHub API error" />);
    expect(screen.getByText('GitHub API error')).toBeInTheDocument();
  });

  it('shows completed state with parent issue link after approval', () => {
    const approvedData: PlanApprovalResponse = {
      plan_id: 'plan-1',
      status: 'completed',
      parent_issue_number: 42,
      parent_issue_url: 'https://github.com/octocat/hello-world/issues/42',
      steps: [
        {
          step_id: 's-1',
          position: 0,
          title: 'Setup OAuth provider',
          description: 'Configure OAuth with GitHub.',
          dependencies: [],
          issue_number: 43,
          issue_url: 'https://github.com/octocat/hello-world/issues/43',
        },
      ],
    };
    render(<PlanPreview plan={createPlan()} approvedData={approvedData} />);
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText(/View Parent Issue #42/)).toBeInTheDocument();
    expect(screen.getByText('#43')).toBeInTheDocument();
  });

  it('shows Exit Plan Mode button for completed plans', () => {
    const onExit = vi.fn().mockResolvedValue(undefined);
    const approvedData: PlanApprovalResponse = {
      plan_id: 'plan-1',
      status: 'completed',
      parent_issue_number: 42,
      parent_issue_url: 'https://github.com/octocat/hello-world/issues/42',
      steps: [],
    };
    render(
      <PlanPreview plan={createPlan()} onExit={onExit} approvedData={approvedData} />,
    );
    expect(screen.getByRole('button', { name: /Exit Plan Mode/ })).toBeInTheDocument();
  });

  it('calls onExit when Exit Plan Mode is clicked', async () => {
    const onExit = vi.fn().mockResolvedValue(undefined);
    const approvedData: PlanApprovalResponse = {
      plan_id: 'plan-1',
      status: 'completed',
      parent_issue_number: 42,
      parent_issue_url: 'https://github.com/octocat/hello-world/issues/42',
      steps: [],
    };
    render(
      <PlanPreview plan={createPlan()} onExit={onExit} approvedData={approvedData} />,
    );
    await userEvent.setup().click(screen.getByRole('button', { name: /Exit Plan Mode/ }));
    expect(onExit).toHaveBeenCalledWith('plan-1');
  });

  it('truncates long summary text', () => {
    const longSummary = 'A'.repeat(600);
    render(<PlanPreview plan={createPlan({ summary: longSummary })} />);
    expect(screen.getByText(/A{500}\.\.\./)).toBeInTheDocument();
  });

  it('does not show action buttons when no handlers provided', () => {
    render(<PlanPreview plan={createPlan()} />);
    expect(screen.queryByRole('button', { name: /Approve/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Request Changes/ })).not.toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <PlanPreview
        plan={createPlan()}
        onApprove={vi.fn().mockResolvedValue({})}
        onRequestChanges={vi.fn()}
      />,
    );
    await expectNoA11yViolations(container);
  });
});
