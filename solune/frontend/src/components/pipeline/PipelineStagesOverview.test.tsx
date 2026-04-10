/**
 * Tests for PipelineStagesOverview component.
 *
 * Covers: column names and item counts, agent assignments,
 * "No agents" state, grid template columns, and heading.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { PipelineStagesOverview } from './PipelineStagesOverview';
import type { StatusColor } from '@/types';

vi.mock('@/components/board/colorUtils', () => ({
  statusColorToCSS: vi.fn(() => '#888'),
}));
vi.mock('@/utils/formatAgentName', () => ({
  formatAgentName: vi.fn((slug: string, display?: string | null) => display || slug),
}));

function createColumn(name: string, itemCount: number, color: StatusColor = 'BLUE') {
  return {
    status: { option_id: `opt-${name}`, name, color },
    item_count: itemCount,
  };
}

describe('PipelineStagesOverview', () => {
  it('renders column names and item counts', () => {
    render(
      <PipelineStagesOverview
        columns={[
          createColumn('Backlog', 5),
          createColumn('In Progress', 3),
        ]}
        localMappings={{}}
        alignedColumnCount={2}
      />,
    );
    expect(screen.getByText('Backlog')).toBeInTheDocument();
    expect(screen.getByText('5 items')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('3 items')).toBeInTheDocument();
  });

  it('renders agent assignments', () => {
    render(
      <PipelineStagesOverview
        columns={[createColumn('Ready', 2)]}
        localMappings={{
          Ready: [
            { id: 'a1', slug: 'copilot', display_name: 'GitHub Copilot' },
            { id: 'a2', slug: 'reviewer', display_name: null },
          ],
        }}
        alignedColumnCount={1}
      />,
    );
    expect(screen.getByText('GitHub Copilot')).toBeInTheDocument();
    expect(screen.getByText('reviewer')).toBeInTheDocument();
  });

  it('shows "No agents" when no agents are mapped', () => {
    render(
      <PipelineStagesOverview
        columns={[createColumn('Done', 10)]}
        localMappings={{}}
        alignedColumnCount={1}
      />,
    );
    expect(screen.getByText('No agents')).toBeInTheDocument();
  });

  it('uses grid template columns based on alignedColumnCount', () => {
    const { container } = render(
      <PipelineStagesOverview
        columns={[createColumn('A', 1), createColumn('B', 2), createColumn('C', 3)]}
        localMappings={{}}
        alignedColumnCount={3}
      />,
    );
    const grid = container.querySelector('.grid') as HTMLElement;
    expect(grid.style.gridTemplateColumns).toBe('repeat(3, minmax(14rem, 1fr))');
  });

  it('has pipeline-stages-title heading', () => {
    render(
      <PipelineStagesOverview
        columns={[createColumn('Backlog', 0)]}
        localMappings={{}}
        alignedColumnCount={1}
      />,
    );
    expect(screen.getByText('Pipeline stages')).toBeInTheDocument();
    const heading = screen.getByText('Pipeline stages');
    expect(heading.id).toBe('pipeline-stages-title');
  });
});
