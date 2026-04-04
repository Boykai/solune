import { describe, expect, it, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { render, screen } from '@/test/test-utils';

import { ToolsEditor } from './ToolsEditor';

const mockState = vi.hoisted(() => ({
  toastInfo: vi.fn(),
  selectedIds: [] as string[],
}));

vi.mock('sonner', () => ({
  toast: {
    info: mockState.toastInfo,
  },
}));

vi.mock('@/components/ui/tooltip', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/components/ui/tooltip')>();
  return {
    ...actual,
    Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

vi.mock('@/components/tools/ToolSelectorModal', () => ({
  ToolSelectorModal: ({ isOpen, onConfirm, onClose }: {
    isOpen: boolean;
    onConfirm: (selectedIds: string[]) => void;
    onClose: () => void;
  }) => {
    if (!isOpen) return null;

    return (
      <div data-testid="tool-selector-modal">
        <button type="button" onClick={() => onConfirm(mockState.selectedIds)}>
          Confirm tool selection
        </button>
        <button type="button" onClick={onClose}>
          Close tool selector
        </button>
      </div>
    );
  },
}));

function renderEditor(overrides: Partial<React.ComponentProps<typeof ToolsEditor>> = {}) {
  const props: React.ComponentProps<typeof ToolsEditor> = {
    tools: ['read', 'write'],
    onToolsChange: vi.fn(),
    projectId: 'PVT_test123',
    ...overrides,
  };

  return {
    ...render(<ToolsEditor {...props} />),
    props,
  };
}

describe('ToolsEditor', () => {
  beforeEach(() => {
    mockState.selectedIds = [];
    mockState.toastInfo.mockReset();
  });

  it('moves tools up in the list', async () => {
    const user = userEvent.setup();
    const { props } = renderEditor();

    await user.click(screen.getByRole('button', { name: 'Move write up' }));

    expect(props.onToolsChange).toHaveBeenCalledWith(['write', 'read']);
  });

  it('removes tools from the list', async () => {
    const user = userEvent.setup();
    const { props } = renderEditor();

    await user.click(screen.getByRole('button', { name: 'Remove read' }));

    expect(props.onToolsChange).toHaveBeenCalledWith(['write']);
  });

  it('shows duplicate feedback while only appending new tools', async () => {
    const user = userEvent.setup();
    const { props } = renderEditor({ tools: ['read'] });
    mockState.selectedIds = ['read', 'lint'];

    await user.click(screen.getByRole('button', { name: /add tools/i }));
    await user.click(screen.getByRole('button', { name: 'Confirm tool selection' }));

    expect(props.onToolsChange).toHaveBeenCalledWith(['read', 'lint']);
    expect(mockState.toastInfo).toHaveBeenCalledWith('1 selected tool was already assigned');
  });

  it('reports duplicate-only selections without emitting a no-op tools change', async () => {
    const user = userEvent.setup();
    const { props } = renderEditor({ tools: ['read'] });
    mockState.selectedIds = ['read'];

    await user.click(screen.getByRole('button', { name: /add tools/i }));
    await user.click(screen.getByRole('button', { name: 'Confirm tool selection' }));

    expect(props.onToolsChange).not.toHaveBeenCalled();
    expect(mockState.toastInfo).toHaveBeenCalledWith('1 selected tool was already assigned');
    expect(screen.queryByTestId('tool-selector-modal')).not.toBeInTheDocument();
  });
});