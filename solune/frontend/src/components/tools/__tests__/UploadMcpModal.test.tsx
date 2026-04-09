import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { fireEvent } from '@testing-library/react';

import { render, screen } from '@/test/test-utils';
import { UploadMcpModal, validateMcpJson } from '../UploadMcpModal';

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

  it('calls onUpload with trimmed form data on valid submit', async () => {
    const user = userEvent.setup();
    const validConfig =
      '{"mcpServers":{"sentry":{"type":"http","url":"https://mcp.sentry.io"}}}';
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
    await user.type(screen.getByLabelText('Name'), '  My Tool  ');
    await user.type(screen.getByLabelText(/description/i), '  Desc  ');
    // Use fireEvent for JSON content since user.type interprets braces as special keys
    const configField = screen.getByLabelText(/mcp configuration/i);
    fireEvent.change(configField, { target: { value: validConfig } });
    await user.click(screen.getByRole('button', { name: /upload$/i }));
    expect(onUpload).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'My Tool', description: 'Desc' }),
    );
  });

  it('validates config JSON before submitting', async () => {
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
    await user.type(screen.getByLabelText('Name'), 'My Tool');
    const configField = screen.getByLabelText(/mcp configuration/i);
    fireEvent.change(configField, { target: { value: 'not valid json' } });
    await user.click(screen.getByRole('button', { name: /upload$/i }));
    expect(screen.getByText('Invalid JSON syntax')).toBeInTheDocument();
    expect(onUpload).not.toHaveBeenCalled();
  });
});

describe('validateMcpJson', () => {
  it('returns error for empty content', () => {
    expect(validateMcpJson('')).toBe('Configuration content is required');
    expect(validateMcpJson('   ')).toBe('Configuration content is required');
  });

  it('returns error for invalid JSON syntax', () => {
    expect(validateMcpJson('{not json')).toBe('Invalid JSON syntax');
  });

  it('returns error for non-object JSON (array)', () => {
    expect(validateMcpJson('[1,2,3]')).toBe('Configuration must be a JSON object');
  });

  it('returns error for non-object JSON (string)', () => {
    expect(validateMcpJson('"hello"')).toBe('Configuration must be a JSON object');
  });

  it('returns error when mcpServers is missing', () => {
    expect(validateMcpJson('{"other": true}')).toBe(
      "Configuration must contain a 'mcpServers' object",
    );
  });

  it('returns error when mcpServers is an array', () => {
    expect(validateMcpJson('{"mcpServers": []}')).toBe(
      "Configuration must contain a 'mcpServers' object",
    );
  });

  it('returns error when mcpServers is empty', () => {
    expect(validateMcpJson('{"mcpServers": {}}')).toBe(
      "'mcpServers' must contain at least one server entry",
    );
  });

  it('returns error when server entry is not an object', () => {
    expect(validateMcpJson('{"mcpServers": {"s": "invalid"}}')).toBe(
      "Server 's' must be an object",
    );
  });

  it('returns error for unknown server type without command or url', () => {
    expect(validateMcpJson('{"mcpServers": {"s": {"type": "unknown"}}}')).toContain(
      "must have 'type'",
    );
  });

  it('returns error when http server lacks url', () => {
    expect(validateMcpJson('{"mcpServers": {"s": {"type": "http"}}}')).toBe(
      "Server 's' must have a 'url' field",
    );
  });

  it('returns error when stdio server lacks command', () => {
    expect(validateMcpJson('{"mcpServers": {"s": {"type": "stdio"}}}')).toBe(
      "Server 's' must have a 'command' field",
    );
  });

  it('accepts valid http server config', () => {
    const config = '{"mcpServers":{"sentry":{"type":"http","url":"https://mcp.sentry.io"}}}';
    expect(validateMcpJson(config)).toBeNull();
  });

  it('accepts valid stdio server config', () => {
    const config = '{"mcpServers":{"local":{"type":"stdio","command":"node","args":["server.js"]}}}';
    expect(validateMcpJson(config)).toBeNull();
  });

  it('infers http type from url field when type is absent', () => {
    const config = '{"mcpServers":{"s":{"url":"https://example.com"}}}';
    expect(validateMcpJson(config)).toBeNull();
  });

  it('infers stdio type from command field when type is absent', () => {
    const config = '{"mcpServers":{"s":{"command":"node"}}}';
    expect(validateMcpJson(config)).toBeNull();
  });

  it('accepts sse server type with url', () => {
    const config = '{"mcpServers":{"s":{"type":"sse","url":"https://example.com/sse"}}}';
    expect(validateMcpJson(config)).toBeNull();
  });

  it('accepts local server type with command', () => {
    const config = '{"mcpServers":{"s":{"type":"local","command":"python3"}}}';
    expect(validateMcpJson(config)).toBeNull();
  });
});
