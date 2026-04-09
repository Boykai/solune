import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { UploadMcpModal } from '../UploadMcpModal';

describe('UploadMcpModal', () => {
  const onClose = vi.fn();
  const onUpload = vi.fn();
  const onUpdate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    onUpload.mockResolvedValue(undefined);
    onUpdate.mockResolvedValue(undefined);
  });

  it('renders nothing when isOpen is false', () => {
    const { container } = render(
      <UploadMcpModal
        isOpen={false}
        onClose={onClose}
        onUpload={onUpload}
        onUpdate={onUpdate}
        isSubmitting={false}
        submitError={null}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders Upload heading in create mode', () => {
    render(
      <UploadMcpModal
        isOpen={true}
        onClose={onClose}
        onUpload={onUpload}
        onUpdate={onUpdate}
        isSubmitting={false}
        submitError={null}
      />,
    );
    expect(screen.getByText('Upload MCP Configuration')).toBeInTheDocument();
  });

  it('renders Edit heading when editingTool is provided', () => {
    const editingTool = {
      id: 'tool-1',
      name: 'Existing Tool',
      description: 'Desc',
      endpoint_url: '',
      config_content: '{"mcpServers":{"test":{"type":"http","url":"https://test.com"}}}',
      sync_status: 'synced' as const,
      sync_error: '',
      synced_at: null,
      github_repo_target: '',
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    render(
      <UploadMcpModal
        isOpen={true}
        onClose={onClose}
        onUpload={onUpload}
        onUpdate={onUpdate}
        isSubmitting={false}
        submitError={null}
        editingTool={editingTool}
      />,
    );
    expect(screen.getByText('Edit MCP Configuration')).toBeInTheDocument();
  });

  it('shows submit error when provided', () => {
    render(
      <UploadMcpModal
        isOpen={true}
        onClose={onClose}
        onUpload={onUpload}
        onUpdate={onUpdate}
        isSubmitting={false}
        submitError="Upload failed"
      />,
    );
    expect(screen.getByText('Upload failed')).toBeInTheDocument();
  });

  it('shows uploading indicator when isSubmitting', () => {
    render(
      <UploadMcpModal
        isOpen={true}
        onClose={onClose}
        onUpload={onUpload}
        onUpdate={onUpdate}
        isSubmitting={true}
        submitError={null}
      />,
    );
    expect(screen.getByText(/uploading and syncing/i)).toBeInTheDocument();
  });

  it('disables submit button when isSubmitting', () => {
    render(
      <UploadMcpModal
        isOpen={true}
        onClose={onClose}
        onUpload={onUpload}
        onUpdate={onUpdate}
        isSubmitting={true}
        submitError={null}
      />,
    );
    expect(screen.getByRole('button', { name: /uploading/i })).toBeDisabled();
  });

  it('calls onClose when Cancel is clicked', async () => {
    const user = userEvent.setup();
    render(
      <UploadMcpModal
        isOpen={true}
        onClose={onClose}
        onUpload={onUpload}
        onUpdate={onUpdate}
        isSubmitting={false}
        submitError={null}
      />,
    );
    await user.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it('validates empty name on submit', async () => {
    const user = userEvent.setup();
    render(
      <UploadMcpModal
        isOpen={true}
        onClose={onClose}
        onUpload={onUpload}
        onUpdate={onUpdate}
        isSubmitting={false}
        submitError={null}
      />,
    );
    await user.click(screen.getByRole('button', { name: /upload$/i }));
    expect(screen.getByText('Name is required')).toBeInTheDocument();
    expect(onUpload).not.toHaveBeenCalled();
  });

  it('shows form fields: name, description, config, repo', () => {
    render(
      <UploadMcpModal
        isOpen={true}
        onClose={onClose}
        onUpload={onUpload}
        onUpdate={onUpdate}
        isSubmitting={false}
        submitError={null}
      />,
    );
    expect(screen.getByLabelText('Name')).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/mcp configuration/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/github repository/i)).toBeInTheDocument();
  });

  it('toggles between paste and file upload mode', async () => {
    const user = userEvent.setup();
    render(
      <UploadMcpModal
        isOpen={true}
        onClose={onClose}
        onUpload={onUpload}
        onUpdate={onUpdate}
        isSubmitting={false}
        submitError={null}
      />,
    );
    // Initially in paste mode
    expect(screen.getByText(/upload file instead/i)).toBeInTheDocument();
    await user.click(screen.getByText(/upload file instead/i));
    expect(screen.getByText(/paste json instead/i)).toBeInTheDocument();
  });

  it('shows duplicate warning when name matches existing', async () => {
    const user = userEvent.setup();
    render(
      <UploadMcpModal
        isOpen={true}
        onClose={onClose}
        onUpload={onUpload}
        onUpdate={onUpdate}
        isSubmitting={false}
        submitError={null}
        existingNames={['Sentry MCP']}
      />,
    );
    const nameInput = screen.getByLabelText('Name');
    await user.type(nameInput, 'Sentry MCP');
    expect(await screen.findByText(/already exists/i)).toBeInTheDocument();
  });

  it('populates fields from initialDraft', () => {
    const draft = {
      name: 'Draft Tool',
      description: 'Draft desc',
      config_content: '{"mcpServers":{"test":{"type":"http","url":"https://t.co"}}}',
      github_repo_target: 'owner/repo',
    };
    render(
      <UploadMcpModal
        isOpen={true}
        onClose={onClose}
        onUpload={onUpload}
        onUpdate={onUpdate}
        isSubmitting={false}
        submitError={null}
        initialDraft={draft}
      />,
    );
    expect(screen.getByLabelText('Name')).toHaveValue('Draft Tool');
  });
});
