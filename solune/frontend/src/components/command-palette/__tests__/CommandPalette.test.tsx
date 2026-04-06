import { describe, it, expect, vi, beforeEach } from 'vitest';

import { render, screen } from '@/test/test-utils';
import { CommandPalette } from '../CommandPalette';

const mocks = vi.hoisted(() => ({
  useCommandPalette: vi.fn(),
}));

vi.mock('@/hooks/useCommandPalette', () => ({
  useCommandPalette: (...args: unknown[]) => mocks.useCommandPalette(...args),
  CATEGORY_META: {
    pages: { label: 'Pages', icon: () => null, order: 0 },
    agents: { label: 'Agents', icon: () => null, order: 1 },
    pipelines: { label: 'Pipelines', icon: () => null, order: 2 },
    tools: { label: 'Tools', icon: () => null, order: 3 },
    chores: { label: 'Chores', icon: () => null, order: 4 },
    apps: { label: 'Apps', icon: () => null, order: 5 },
    actions: { label: 'Actions', icon: () => null, order: 6 },
  },
}));

describe('CommandPalette', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.useCommandPalette.mockReturnValue({
      query: '',
      setQuery: vi.fn(),
      results: [],
      selectedIndex: 0,
      moveUp: vi.fn(),
      moveDown: vi.fn(),
      selectCurrent: vi.fn(),
      isLoading: false,
    });
  });

  it('prevents Tab from escaping when the dialog has no focusable elements', () => {
    render(<CommandPalette isOpen={true} onClose={vi.fn()} projectId="proj-1" />);

    const dialog = screen.getByRole('dialog', { name: /command palette/i });
    Object.defineProperty(dialog, 'querySelectorAll', {
      configurable: true,
      value: vi.fn(() => []),
    });

    const event = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true });
    document.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
  });

  it('closes on Escape', () => {
    const onClose = vi.fn();
    render(<CommandPalette isOpen={true} onClose={onClose} projectId="proj-1" />);

    const event = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true });
    document.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
    expect(onClose).toHaveBeenCalledOnce();
  });
});
