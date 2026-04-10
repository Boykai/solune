/**
 * Tests for Dialog component.
 *
 * Covers: trigger rendering, dialog opening, title/description display,
 * Escape key dismissal, default close button, and hideClose prop.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/test-utils';
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../dialog';

function renderDialog({ hideClose = false }: { hideClose?: boolean } = {}) {
  const onOpenChange = vi.fn();
  const result = render(
    <Dialog onOpenChange={onOpenChange}>
      <DialogTrigger>Open Dialog</DialogTrigger>
      <DialogContent hideClose={hideClose}>
        <DialogHeader>
          <DialogTitle>Edit profile</DialogTitle>
          <DialogDescription>Make changes to your profile here.</DialogDescription>
        </DialogHeader>
      </DialogContent>
    </Dialog>,
  );
  return { ...result, onOpenChange };
}

describe('Dialog', () => {
  it('renders trigger and opens dialog on click', async () => {
    renderDialog();
    expect(screen.queryByText('Edit profile')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Open Dialog'));
    await waitFor(() => {
      expect(screen.getByText('Edit profile')).toBeInTheDocument();
    });
  });

  it('shows title and description', async () => {
    renderDialog();
    fireEvent.click(screen.getByText('Open Dialog'));

    await waitFor(() => {
      expect(screen.getByText('Edit profile')).toBeInTheDocument();
      expect(screen.getByText('Make changes to your profile here.')).toBeInTheDocument();
    });
  });

  it('closes on Escape key', async () => {
    renderDialog();
    fireEvent.click(screen.getByText('Open Dialog'));

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('has close button by default', async () => {
    renderDialog();
    fireEvent.click(screen.getByText('Open Dialog'));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Close' })).toBeInTheDocument();
    });
  });

  it('hides close button when hideClose is true', async () => {
    renderDialog({ hideClose: true });
    fireEvent.click(screen.getByText('Open Dialog'));

    await waitFor(() => {
      expect(screen.getByText('Edit profile')).toBeInTheDocument();
    });

    expect(screen.queryByRole('button', { name: 'Close' })).not.toBeInTheDocument();
  });
});
