import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { EditRepoMcpModal } from '../EditRepoMcpModal';
import type { RepoMcpServerConfig } from '@/types';

function createMockServer(overrides: Partial<RepoMcpServerConfig> = {}): RepoMcpServerConfig {
  return {
    name: 'sentry',
    config: { type: 'http', url: 'https://mcp.sentry.io' },
    source_paths: ['.copilot/mcp.json'],
    ...overrides,
  };
}

describe('EditRepoMcpModal', () => {
  const onClose = vi.fn();
  const onSave = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    onSave.mockResolvedValue(undefined);
  });

  it('renders nothing when isOpen is false', () => {
    const { container } = render(
      <EditRepoMcpModal
        isOpen={false}
        server={null}
        isSubmitting={false}
        submitError={null}
        onClose={onClose}
        onSave={onSave}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders the modal with form fields when open', async () => {
    const server = createMockServer();
    render(
      <EditRepoMcpModal
        isOpen={true}
        server={server}
        isSubmitting={false}
        submitError={null}
        onClose={onClose}
        onSave={onSave}
      />,
    );
    expect(screen.getByText('Edit Repository MCP')).toBeInTheDocument();
    // Dialog renders with initial state set during render via derived-state pattern
    const nameInput = screen.getByLabelText('Name') as HTMLInputElement;
    expect(nameInput).toBeInTheDocument();
    expect(screen.getByLabelText('MCP Configuration')).toBeInTheDocument();
  });

  it('populates config textarea with formatted JSON', () => {
    const server = createMockServer();
    // Render closed first, then open — modal populates fields on open transition
    const { rerender } = render(
      <EditRepoMcpModal
        isOpen={false}
        server={null}
        isSubmitting={false}
        submitError={null}
        onClose={onClose}
        onSave={onSave}
      />,
    );
    rerender(
      <EditRepoMcpModal
        isOpen={true}
        server={server}
        isSubmitting={false}
        submitError={null}
        onClose={onClose}
        onSave={onSave}
      />,
    );
    const nameInput = screen.getByLabelText('Name') as HTMLInputElement;
    const textarea = screen.getByLabelText('MCP Configuration') as HTMLTextAreaElement;
    expect(nameInput.value).toBe('sentry');
    expect(textarea.value).toContain('"mcpServers"');
    expect(textarea.value).toContain('"sentry"');
  });

  it('shows submit error when provided', () => {
    const server = createMockServer();
    render(
      <EditRepoMcpModal
        isOpen={true}
        server={server}
        isSubmitting={false}
        submitError="Failed to save"
        onClose={onClose}
        onSave={onSave}
      />,
    );
    expect(screen.getByText('Failed to save')).toBeInTheDocument();
  });

  it('shows saving indicator when isSubmitting', () => {
    const server = createMockServer();
    render(
      <EditRepoMcpModal
        isOpen={true}
        server={server}
        isSubmitting={true}
        submitError={null}
        onClose={onClose}
        onSave={onSave}
      />,
    );
    expect(screen.getByText(/saving repository mcp/i)).toBeInTheDocument();
  });

  it('disables Save button when submitting', () => {
    const server = createMockServer();
    render(
      <EditRepoMcpModal
        isOpen={true}
        server={server}
        isSubmitting={true}
        submitError={null}
        onClose={onClose}
        onSave={onSave}
      />,
    );
    expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled();
  });

  it('calls onClose when Cancel is clicked', async () => {
    const user = userEvent.setup();
    const server = createMockServer();
    render(
      <EditRepoMcpModal
        isOpen={true}
        server={server}
        isSubmitting={false}
        submitError={null}
        onClose={onClose}
        onSave={onSave}
      />,
    );
    await user.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it('validates empty name on submit', async () => {
    const user = userEvent.setup();
    const server = createMockServer();
    render(
      <EditRepoMcpModal
        isOpen={true}
        server={server}
        isSubmitting={false}
        submitError={null}
        onClose={onClose}
        onSave={onSave}
      />,
    );
    const nameInput = screen.getByLabelText('Name');
    await user.clear(nameInput);
    await user.click(screen.getByRole('button', { name: /save changes/i }));
    expect(screen.getByText('Name is required')).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });
});
