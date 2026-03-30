import { describe, it, expect, vi } from 'vitest';
import { render, screen, userEvent } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';

import { RefreshButton } from './RefreshButton';

describe('RefreshButton', () => {
  it('renders with refresh label', () => {
    render(<RefreshButton onRefresh={vi.fn()} isRefreshing={false} />);
    expect(screen.getByRole('button', { name: /refresh board data/i })).toBeInTheDocument();
  });

  it('calls onRefresh when clicked', async () => {
    const onRefresh = vi.fn();
    render(<RefreshButton onRefresh={onRefresh} isRefreshing={false} />);
    const user = userEvent.setup();

    await user.click(screen.getByRole('button'));

    expect(onRefresh).toHaveBeenCalledOnce();
  });

  it('is disabled when isRefreshing is true', () => {
    render(<RefreshButton onRefresh={vi.fn()} isRefreshing={true} />);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('is disabled when disabled prop is true', () => {
    render(<RefreshButton onRefresh={vi.fn()} isRefreshing={false} disabled={true} />);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('applies spin animation when refreshing', () => {
    const { container } = render(<RefreshButton onRefresh={vi.fn()} isRefreshing={true} />);
    const icon = container.querySelector('svg');
    expect(icon?.className).toContain('animate-spin');
  });

  it('does not spin when idle', () => {
    const { container } = render(<RefreshButton onRefresh={vi.fn()} isRefreshing={false} />);
    const icon = container.querySelector('svg');
    expect(icon?.className).not.toContain('animate-spin');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<RefreshButton onRefresh={vi.fn()} isRefreshing={false} />);
    await expectNoA11yViolations(container);
  });
});
