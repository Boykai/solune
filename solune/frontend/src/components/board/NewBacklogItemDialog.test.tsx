/**
 * Tests for NewBacklogItemDialog — modal replacing the legacy Parent Issue
 * Intake panel. Covers validation, file import, pipeline selection, successful
 * launch (dialog closes), and launch failure (dialog stays open).
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement } from 'react';
import { render, screen, userEvent, waitFor } from '@/test/test-utils';
import { NewBacklogItemDialog } from './NewBacklogItemDialog';
import { pipelinesApi } from '@/services/api';
import type { PipelineConfigSummary } from '@/types';

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api');
  return {
    ...actual,
    pipelinesApi: {
      ...actual.pipelinesApi,
      launch: vi.fn(),
    },
  };
});

const mockLaunch = vi.mocked(pipelinesApi.launch);

const PIPELINES: PipelineConfigSummary[] = [
  {
    id: 'pipe-1',
    name: 'Spec Kit Flow',
    description: 'Default spec workflow',
    stage_count: 4,
    agent_count: 6,
    total_tool_count: 0,
    is_preset: false,
    preset_id: '',
    stages: [],
    updated_at: '2026-03-10T00:00:00Z',
  },
];

function renderDialog(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(ui, {
    wrapper: ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  });
}

describe('NewBacklogItemDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render any form fields when closed', () => {
    renderDialog(
      <NewBacklogItemDialog
        open={false}
        onOpenChange={vi.fn()}
        projectId="PVT_1"
        pipelines={PIPELINES}
        isLoadingPipelines={false}
        pipelinesError={null}
        onRetryPipelines={vi.fn()}
      />
    );

    expect(screen.queryByLabelText('GitHub Parent Issue Description')).not.toBeInTheDocument();
  });

  it('renders the dialog with description and pipeline fields when open', () => {
    renderDialog(
      <NewBacklogItemDialog
        open
        onOpenChange={vi.fn()}
        projectId="PVT_1"
        pipelines={PIPELINES}
        isLoadingPipelines={false}
        pipelinesError={null}
        onRetryPipelines={vi.fn()}
      />
    );

    expect(screen.getByRole('dialog', { name: /new backlog item/i })).toBeInTheDocument();
    expect(screen.getByLabelText('GitHub Parent Issue Description')).toBeInTheDocument();
    expect(screen.getByLabelText('Agent Pipeline Config')).toBeInTheDocument();
  });

  it('shows inline validation errors when the form is empty', async () => {
    renderDialog(
      <NewBacklogItemDialog
        open
        onOpenChange={vi.fn()}
        projectId="PVT_1"
        pipelines={PIPELINES}
        isLoadingPipelines={false}
        pipelinesError={null}
        onRetryPipelines={vi.fn()}
      />
    );

    await userEvent.click(screen.getByRole('button', { name: 'Launch pipeline' }));

    expect(
      screen.getByText('Paste or upload the parent issue description first.')
    ).toBeInTheDocument();
    expect(
      screen.getByText('Select an Agent Pipeline Config before launching.')
    ).toBeInTheDocument();
    expect(mockLaunch).not.toHaveBeenCalled();
  });

  it('launches the selected pipeline and closes the dialog on success', async () => {
    const onLaunchedMock = vi.fn();
    const onOpenChangeMock = vi.fn();
    mockLaunch.mockResolvedValue({
      success: true,
      issue_number: 42,
      issue_url: 'https://github.com/owner/repo/issues/42',
      message: 'Issue #42 created and launched.',
    });

    renderDialog(
      <NewBacklogItemDialog
        open
        onOpenChange={onOpenChangeMock}
        projectId="PVT_1"
        projectName="Solune"
        pipelines={PIPELINES}
        isLoadingPipelines={false}
        pipelinesError={null}
        onRetryPipelines={vi.fn()}
        onLaunched={onLaunchedMock}
      />
    );

    await userEvent.type(
      screen.getByLabelText('GitHub Parent Issue Description'),
      '# Import existing issue\n\nPreserve this parent issue context.'
    );
    await userEvent.selectOptions(screen.getByLabelText('Agent Pipeline Config'), 'pipe-1');
    await userEvent.click(screen.getByRole('button', { name: 'Launch pipeline' }));

    await waitFor(() => {
      expect(mockLaunch).toHaveBeenCalledWith('PVT_1', {
        issue_description: '# Import existing issue\n\nPreserve this parent issue context.',
        pipeline_id: 'pipe-1',
      });
    });

    expect(onLaunchedMock).toHaveBeenCalledWith(
      expect.objectContaining({ success: true, issue_number: 42 })
    );
    expect(onOpenChangeMock).toHaveBeenCalledWith(false);
  });

  it('keeps the dialog open and shows the error when launch fails', async () => {
    const onLaunchedMock = vi.fn();
    const onOpenChangeMock = vi.fn();
    mockLaunch.mockResolvedValue({
      success: false,
      issue_number: 84,
      issue_url: 'https://github.com/owner/repo/issues/84',
      message: 'The selected pipeline could not be started.',
    });

    renderDialog(
      <NewBacklogItemDialog
        open
        onOpenChange={onOpenChangeMock}
        projectId="PVT_1"
        pipelines={PIPELINES}
        isLoadingPipelines={false}
        pipelinesError={null}
        onRetryPipelines={vi.fn()}
        onLaunched={onLaunchedMock}
      />
    );

    await userEvent.type(screen.getByLabelText('GitHub Parent Issue Description'), '# Retry me');
    await userEvent.selectOptions(screen.getByLabelText('Agent Pipeline Config'), 'pipe-1');
    await userEvent.click(screen.getByRole('button', { name: 'Launch pipeline' }));

    expect(await screen.findByText('Launch failed')).toBeInTheDocument();
    expect(screen.getByText('The selected pipeline could not be started.')).toBeInTheDocument();
    expect(screen.getByLabelText('GitHub Parent Issue Description')).toHaveValue('# Retry me');
    expect(screen.getByLabelText('Agent Pipeline Config')).toHaveValue('pipe-1');
    expect(onLaunchedMock).not.toHaveBeenCalled();
    expect(onOpenChangeMock).not.toHaveBeenCalledWith(false);
  });

  it('imports supported markdown files into the textarea', async () => {
    renderDialog(
      <NewBacklogItemDialog
        open
        onOpenChange={vi.fn()}
        projectId="PVT_1"
        pipelines={PIPELINES}
        isLoadingPipelines={false}
        pipelinesError={null}
        onRetryPipelines={vi.fn()}
      />
    );

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['# Imported issue\n\nLoaded from disk.'], 'issue.md', {
      type: 'text/markdown',
    });

    await userEvent.upload(fileInput, file);

    await waitFor(() => {
      expect(screen.getByLabelText('GitHub Parent Issue Description')).toHaveValue(
        '# Imported issue\n\nLoaded from disk.'
      );
    });
    expect(screen.getByText('Imported issue.md')).toBeInTheDocument();
  });

  it('rejects unsupported file types with an inline error', async () => {
    renderDialog(
      <NewBacklogItemDialog
        open
        onOpenChange={vi.fn()}
        projectId="PVT_1"
        pipelines={PIPELINES}
        isLoadingPipelines={false}
        pipelinesError={null}
        onRetryPipelines={vi.fn()}
      />
    );

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['binary'], 'issue.png', { type: 'image/png' });
    const user = userEvent.setup({ applyAccept: false });

    await user.upload(fileInput, file);

    expect(
      screen.getByText(
        'Only Markdown (.md), plain-text (.txt), WebVTT (.vtt), and SubRip (.srt) files are supported.'
      )
    ).toBeInTheDocument();
    expect(mockLaunch).not.toHaveBeenCalled();
  });

  it('renders the pipeline loading error state and retries on request', async () => {
    const onRetryPipelines = vi.fn();
    const user = userEvent.setup();

    renderDialog(
      <NewBacklogItemDialog
        open
        onOpenChange={vi.fn()}
        projectId="PVT_1"
        pipelines={PIPELINES}
        isLoadingPipelines={false}
        pipelinesError="Could not load pipeline configs."
        onRetryPipelines={onRetryPipelines}
      />
    );

    expect(screen.getByText('Could not load pipeline configs.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Retry loading configs' }));
    expect(onRetryPipelines).toHaveBeenCalledTimes(1);
  });

  it('invokes onOpenChange(false) when the Cancel button is clicked', async () => {
    const onOpenChangeMock = vi.fn();

    renderDialog(
      <NewBacklogItemDialog
        open
        onOpenChange={onOpenChangeMock}
        projectId="PVT_1"
        pipelines={PIPELINES}
        isLoadingPipelines={false}
        pipelinesError={null}
        onRetryPipelines={vi.fn()}
      />
    );

    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onOpenChangeMock).toHaveBeenCalledWith(false);
  });
});
