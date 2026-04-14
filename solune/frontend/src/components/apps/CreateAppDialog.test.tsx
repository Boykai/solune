import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, userEvent } from '@/test/test-utils';
import type { ComponentProps } from 'react';
import { CreateAppDialog } from './CreateAppDialog';
import type { AppCreate } from '@/types/apps';

const defaultProps: ComponentProps<typeof CreateAppDialog> = {
  onClose: vi.fn(),
  onSubmit: vi.fn(),
  isPending: false,
  owners: [{ login: 'test-owner', avatar_url: 'https://example.test/avatar.png', type: 'User' }],
  getErrorMessage: (_err: unknown, fallback: string) => fallback,
  pipelines: [{
    id: 'pipe-1',
    name: 'Default Pipeline',
    description: '',
    stage_count: 0,
    agent_count: 0,
    total_tool_count: 0,
    is_preset: false,
    preset_id: '',
    stages: [],
    updated_at: '2026-01-01T00:00:00Z',
  }],
  isLoadingPipelines: false,
  defaultPipelineId: 'pipe-1',
  projectId: 'PVT_proj123',
};

function renderDialog(overrides: Partial<ComponentProps<typeof CreateAppDialog>> = {}) {
  return render(<CreateAppDialog {...defaultProps} {...overrides} />);
}

async function fillAndSubmit(
  user: ReturnType<typeof userEvent.setup>,
  { displayName = 'Test App' }: { displayName?: string } = {}
) {
  const input = screen.getByLabelText('Display Name');
  await user.clear(input);
  await user.type(input, displayName);

  const submitBtn = screen.getByRole('button', { name: /^Create App$|^Create Repository/i });
  await user.click(submitBtn);
}

function capturedPayload(): AppCreate | undefined {
  const calls = (defaultProps.onSubmit as ReturnType<typeof vi.fn>).mock.calls;
  return calls.length > 0 ? (calls[0][0] as AppCreate) : undefined;
}

describe('CreateAppDialog — project_id scoping (T015)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('same-repo payload includes project_id when projectId is set', async () => {
    const user = userEvent.setup();
    renderDialog({ initialRepoType: 'same-repo' });
    await fillAndSubmit(user);

    const payload = capturedPayload();
    expect(payload).toBeDefined();
    expect(payload!.repo_type).toBe('same-repo');
    expect(payload!.pipeline_id).toBe('pipe-1');
    expect(payload!.project_id).toBe('PVT_proj123');
    expect(payload!.branch).toBe('main');
  });

  it('new-repo payload omits project_id', async () => {
    const user = userEvent.setup();
    renderDialog({ initialRepoType: 'new-repo' });
    await fillAndSubmit(user);

    const payload = capturedPayload();
    expect(payload).toBeDefined();
    expect(payload!.repo_type).toBe('new-repo');
    expect(payload!.project_id).toBeUndefined();
  });

  it('external-repo payload defaults branch to main', async () => {
    const user = userEvent.setup();
    renderDialog({ initialRepoType: 'external-repo' });

    const input = screen.getByLabelText('Display Name');
    await user.clear(input);
    await user.type(input, 'Ext App');

    // Fill external repo URL
    const urlInput = screen.getByPlaceholderText(/github\.com/i);
    await user.type(urlInput, 'https://github.com/owner/repo');

    const submitBtn = screen.getByRole('button', { name: /Create App/i });
    await user.click(submitBtn);

    const payload = capturedPayload();
    expect(payload).toBeDefined();
    expect(payload!.repo_type).toBe('external-repo');
    expect(payload!.project_id).toBeUndefined();
    expect(payload!.branch).toBe('main');
  });
});

describe('CreateAppDialog — removed fields and layout changes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render a Target Branch input for same-repo type', () => {
    renderDialog({ initialRepoType: 'same-repo' });
    expect(screen.queryByLabelText(/target branch/i)).not.toBeInTheDocument();
  });

  it('does not render a Target Branch input for external-repo type', () => {
    renderDialog({ initialRepoType: 'external-repo' });
    expect(screen.queryByLabelText(/target branch/i)).not.toBeInTheDocument();
  });

  it('does not render a Name Override input in Advanced options', async () => {
    const user = userEvent.setup();
    renderDialog({ initialRepoType: 'same-repo' });

    // Expand advanced options
    await user.click(screen.getByRole('button', { name: /advanced options/i }));

    expect(screen.queryByLabelText(/name override/i)).not.toBeInTheDocument();
  });

  it('shows branch as "main" in the derived-name preview for same-repo', async () => {
    const user = userEvent.setup();
    renderDialog({ initialRepoType: 'same-repo' });

    await user.type(screen.getByLabelText('Display Name'), 'My Feature');

    expect(screen.getByText('main')).toBeInTheDocument();
  });

  it('does not render New Repository Settings outside Advanced for new-repo', () => {
    renderDialog({ initialRepoType: 'new-repo' });

    // New Repo Settings should not be visible until Advanced is expanded
    expect(screen.queryByText('New Repository Settings')).not.toBeInTheDocument();
  });

  it('renders New Repository Settings inside Advanced options for new-repo', async () => {
    const user = userEvent.setup();
    renderDialog({ initialRepoType: 'new-repo' });

    // Expand advanced options
    await user.click(screen.getByRole('button', { name: /advanced options/i }));

    expect(screen.getByText('New Repository Settings')).toBeInTheDocument();
    expect(screen.getByLabelText('Owner')).toBeInTheDocument();
  });

  it('new-repo payload does not include branch (new repos use default)', async () => {
    const user = userEvent.setup();
    renderDialog({ initialRepoType: 'new-repo' });
    await fillAndSubmit(user);

    const payload = capturedPayload();
    expect(payload).toBeDefined();
    expect(payload!.branch).toBeUndefined();
  });

  it('rejects display names that cannot produce a slug', async () => {
    const user = userEvent.setup();
    renderDialog({ initialRepoType: 'same-repo' });

    await fillAndSubmit(user, { displayName: '!!!' });

    expect(screen.getByText('Display name must include at least one letter or number.')).toBeInTheDocument();
    expect(defaultProps.onSubmit).not.toHaveBeenCalled();
  });
});
