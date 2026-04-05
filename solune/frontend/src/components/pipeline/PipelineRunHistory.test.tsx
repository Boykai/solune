import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { fireEvent } from '@testing-library/react';
import { renderWithProviders, screen, waitFor } from '@/test/test-utils';
import { PipelineRunHistory } from './PipelineRunHistory';

const mockListRuns = vi.fn();

vi.mock('@/services/api', () => ({
  pipelinesApi: {
    listRuns: (...args: unknown[]) => mockListRuns(...args),
  },
}));

describe('PipelineRunHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(Date, 'now').mockReturnValue(new Date('2026-04-05T12:00:00.000Z').getTime());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads runs lazily when expanded and can be collapsed again', async () => {
    mockListRuns.mockResolvedValue({
      runs: [],
    });

    renderWithProviders(<PipelineRunHistory pipelineId="pipe-1" />);

    expect(mockListRuns).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: /run history/i }));
    await waitFor(() => expect(mockListRuns).toHaveBeenCalledWith('pipe-1', { limit: 20 }));
    expect(await screen.findByText('No runs recorded yet')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /run history/i }));
    expect(screen.queryByText('No runs recorded yet')).not.toBeInTheDocument();
  });

  it('renders duration formatting and status badges for returned runs', async () => {
    mockListRuns.mockResolvedValue({
      runs: [
        {
          id: 'run-1',
          status: 'completed',
          started_at: '2026-04-05T11:59:00.000Z',
          completed_at: '2026-04-05T12:01:05.000Z',
        },
        {
          id: 'run-2',
          status: 'failed',
          started_at: '2026-04-05T11:58:30.000Z',
          completed_at: '2026-04-05T11:59:00.000Z',
        },
      ],
    });

    renderWithProviders(<PipelineRunHistory pipelineId="pipe-1" />);

    fireEvent.click(screen.getByRole('button', { name: /run history/i }));

    expect(await screen.findByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('2m 5s')).toBeInTheDocument();
    expect(screen.getByText('30s')).toBeInTheDocument();
    expect(screen.getAllByText('1m ago')).toHaveLength(2);
  });

  it('shows the loading state while the query is in flight', async () => {
    let resolveRuns: ((value: { runs: never[] }) => void) | undefined;
    mockListRuns.mockImplementation(
      () =>
        new Promise<{ runs: never[] }>((resolve) => {
          resolveRuns = resolve;
        }),
    );

    renderWithProviders(<PipelineRunHistory pipelineId="pipe-1" />);

    fireEvent.click(screen.getByRole('button', { name: /run history/i }));
    expect(screen.getByText('Loading…')).toBeInTheDocument();

    resolveRuns?.({ runs: [] });
    expect(await screen.findByText('No runs recorded yet')).toBeInTheDocument();
  });
});
