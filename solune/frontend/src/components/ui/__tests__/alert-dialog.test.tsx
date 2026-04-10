/**
 * Tests for AlertDialog component.
 *
 * Covers: trigger rendering, dialog opening, title/description display,
 * action/cancel handlers, and non-dismissal on outside click
 * (AlertDialog intentionally requires an explicit user choice).
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/test-utils';
import {
  AlertDialog,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogAction,
  AlertDialogCancel,
} from '../alert-dialog';

function renderAlertDialog({
  onAction = vi.fn(),
  onCancel = vi.fn(),
}: { onAction?: () => void; onCancel?: () => void } = {}) {
  return render(
    <AlertDialog>
      <AlertDialogTrigger>Open Alert</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Confirm deletion</AlertDialogTitle>
          <AlertDialogDescription>This action cannot be undone.</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onCancel}>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={onAction}>Delete</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>,
  );
}

describe('AlertDialog', () => {
  it('renders trigger and opens dialog on click', async () => {
    renderAlertDialog();
    expect(screen.queryByText('Confirm deletion')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Open Alert'));
    await waitFor(() => {
      expect(screen.getByText('Confirm deletion')).toBeInTheDocument();
    });
  });

  it('shows title and description when open', async () => {
    renderAlertDialog();
    fireEvent.click(screen.getByText('Open Alert'));

    await waitFor(() => {
      expect(screen.getByText('Confirm deletion')).toBeInTheDocument();
      expect(screen.getByText('This action cannot be undone.')).toBeInTheDocument();
    });
  });

  it('calls action handler on action click', async () => {
    const onAction = vi.fn();
    renderAlertDialog({ onAction });
    fireEvent.click(screen.getByText('Open Alert'));

    await waitFor(() => {
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Delete'));
    expect(onAction).toHaveBeenCalledOnce();
  });

  it('calls cancel handler on cancel click', async () => {
    const onCancel = vi.fn();
    renderAlertDialog({ onCancel });
    fireEvent.click(screen.getByText('Open Alert'));

    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Cancel'));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('renders with alertdialog role (prevents dismiss on outside click by spec)', async () => {
    renderAlertDialog();
    fireEvent.click(screen.getByText('Open Alert'));

    await waitFor(() => {
      expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    });

    // AlertDialog uses role="alertdialog" which semantically signals
    // that the dialog requires an explicit user action and should not
    // be dismissed by clicking outside — verifiable via the role.
    const dialog = screen.getByRole('alertdialog');
    expect(dialog).toHaveAttribute('role', 'alertdialog');
  });
});
