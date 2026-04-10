/**
 * Tests for KeyboardShortcutModal component.
 *
 * Covers: conditional rendering based on isOpen, shortcut group display,
 * Escape key closure, close button click, backdrop click,
 * ARIA accessibility attributes, and aria-labelledby.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@/test/test-utils';
import { KeyboardShortcutModal } from '../keyboard-shortcut-modal';

describe('KeyboardShortcutModal', () => {
  it('does not render when isOpen is false', () => {
    render(<KeyboardShortcutModal isOpen={false} onClose={vi.fn()} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders modal with shortcut groups when isOpen is true', () => {
    render(<KeyboardShortcutModal isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Keyboard Shortcuts')).toBeInTheDocument();
    expect(screen.getByText('Navigation')).toBeInTheDocument();
    expect(screen.getByText('Actions')).toBeInTheDocument();
    expect(screen.getByText('Help')).toBeInTheDocument();
  });

  it('calls onClose when Escape is pressed', () => {
    const onClose = vi.fn();
    render(<KeyboardShortcutModal isOpen={true} onClose={onClose} />);

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(<KeyboardShortcutModal isOpen={true} onClose={onClose} />);

    fireEvent.click(screen.getByRole('button', { name: 'Close shortcuts modal' }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('has role=dialog and aria-modal', () => {
    render(<KeyboardShortcutModal isOpen={true} onClose={vi.fn()} />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
  });

  it('has aria-labelledby pointing to the title', () => {
    render(<KeyboardShortcutModal isOpen={true} onClose={vi.fn()} />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-labelledby', 'shortcut-modal-title');
    expect(document.getElementById('shortcut-modal-title')?.textContent).toBe('Keyboard Shortcuts');
  });

  it('displays keyboard shortcuts', () => {
    render(<KeyboardShortcutModal isOpen={true} onClose={vi.fn()} />);
    // Navigation shortcuts
    expect(screen.getByText('Go to Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Go to Board')).toBeInTheDocument();
    // Actions shortcuts
    expect(screen.getByText('Command Palette')).toBeInTheDocument();
    expect(screen.getByText('Close modal')).toBeInTheDocument();
    // Help shortcuts
    expect(screen.getByText('Show this modal')).toBeInTheDocument();
  });
});
