import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { render, screen } from '@/test/test-utils';
import { ToolChips } from '../ToolChips';
import type { ToolChip } from '@/types';

function createMockChip(overrides: Partial<ToolChip> = {}): ToolChip {
  return {
    id: 'chip-1',
    name: 'Sentry',
    description: 'Error tracking',
    ...overrides,
  };
}

describe('ToolChips', () => {
  const onRemove = vi.fn();
  const onAddClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders chip names', () => {
    const tools = [
      createMockChip({ id: 'c1', name: 'Sentry' }),
      createMockChip({ id: 'c2', name: 'Linear' }),
    ];
    render(<ToolChips tools={tools} onRemove={onRemove} onAddClick={onAddClick} />);
    expect(screen.getByText('Sentry')).toBeInTheDocument();
    expect(screen.getByText('Linear')).toBeInTheDocument();
  });

  it('calls onRemove with the correct id when remove button is clicked', async () => {
    const user = userEvent.setup();
    const tools = [createMockChip({ id: 'c1', name: 'Sentry' })];
    render(<ToolChips tools={tools} onRemove={onRemove} onAddClick={onAddClick} />);
    await user.click(screen.getByRole('button', { name: /remove sentry/i }));
    expect(onRemove).toHaveBeenCalledWith('c1');
  });

  it('calls onAddClick when add button is clicked', async () => {
    const user = userEvent.setup();
    const tools = [createMockChip()];
    render(<ToolChips tools={tools} onRemove={onRemove} onAddClick={onAddClick} />);
    await user.click(screen.getByRole('button', { name: /add more/i }));
    expect(onAddClick).toHaveBeenCalled();
  });

  it('shows "Add Tools" when no tools are present', () => {
    render(<ToolChips tools={[]} onRemove={onRemove} onAddClick={onAddClick} />);
    expect(screen.getByRole('button', { name: /add tools/i })).toBeInTheDocument();
  });

  it('shows "+ Add more" when tools are present', () => {
    const tools = [createMockChip()];
    render(<ToolChips tools={tools} onRemove={onRemove} onAddClick={onAddClick} />);
    expect(screen.getByText('+ Add more')).toBeInTheDocument();
  });
});
