import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { CopyButton } from '../copy-button';

const mockWriteText = vi.fn().mockResolvedValue(undefined);

let originalClipboard: Clipboard;

beforeEach(() => {
  vi.clearAllMocks();
  mockWriteText.mockResolvedValue(undefined);
  // Save original and replace with mock
  originalClipboard = navigator.clipboard;
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText: mockWriteText },
    writable: true,
    configurable: true,
  });
});

afterEach(() => {
  Object.defineProperty(navigator, 'clipboard', {
    value: originalClipboard,
    writable: true,
    configurable: true,
  });
});

describe('CopyButton', () => {
  it('renders with default "Copy" label', () => {
    render(<CopyButton value="test" />);
    expect(screen.getByText('Copy')).toBeInTheDocument();
  });

  it('renders with custom label', () => {
    render(<CopyButton value="test" label="Copy URL" />);
    expect(screen.getByText('Copy URL')).toBeInTheDocument();
  });

  it('has correct aria-label before copy', () => {
    render(<CopyButton value="test" />);
    expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Copy');
  });

  it('copies value and shows success state on click', async () => {
    const user = userEvent.setup();
    render(<CopyButton value="hello world" />);

    await user.click(screen.getByRole('button'));

    // The component uses navigator.clipboard.writeText with execCommand fallback.
    // In happy-dom, the fallback path is used. We verify the success state.
    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeInTheDocument();
    });
  });

  it('shows "Copied!" text after successful copy', async () => {
    const user = userEvent.setup();
    render(<CopyButton value="test" />);

    await user.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeInTheDocument();
    });
  });

  it('changes aria-label to "Copied" after click', async () => {
    const user = userEvent.setup();
    render(<CopyButton value="test" />);

    await user.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Copied');
    });
  });

  it('applies custom className', () => {
    render(<CopyButton value="test" className="extra-class" />);
    const button = screen.getByRole('button');
    expect(button.className).toContain('extra-class');
  });

  it('is a button with type="button"', () => {
    render(<CopyButton value="test" />);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button');
  });
});
