import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';

import { ProjectBoardErrorBanners } from './ProjectBoardErrorBanners';

const noErrorProps = {
  showRateLimitBanner: false,
  rateLimitRetryAfter: undefined,
  isRateLimitLow: false,
  rateLimitInfo: null,
  refreshError: null,
  projectsError: null,
  projectsRateLimitError: false,
  boardError: null,
  boardLoading: false,
  boardRateLimitError: false,
  selectedProjectId: 'PVT_1',
  onRetryBoard: vi.fn(),
};

describe('ProjectBoardErrorBanners', () => {
  it('renders nothing when there are no errors', () => {
    const { container } = render(<ProjectBoardErrorBanners {...noErrorProps} />);
    expect(container.querySelectorAll('[role="alert"]')).toHaveLength(0);
  });

  it('shows rate limit banner when showRateLimitBanner is true', () => {
    render(<ProjectBoardErrorBanners {...noErrorProps} showRateLimitBanner={true} />);
    expect(screen.getByText('Rate limit reached')).toBeInTheDocument();
  });

  it('shows rate limit low warning', () => {
    render(
      <ProjectBoardErrorBanners
        {...noErrorProps}
        isRateLimitLow={true}
        rateLimitInfo={{ remaining: 5, reset_at: Date.now() + 60000 }}
      />
    );
    expect(screen.getByText('Rate limit low')).toBeInTheDocument();
    expect(screen.getByText(/5 API requests remaining/)).toBeInTheDocument();
  });

  it('shows refresh error banner', () => {
    render(
      <ProjectBoardErrorBanners
        {...noErrorProps}
        refreshError={{ type: 'network', message: 'Network failed' }}
      />
    );
    expect(screen.getByText('Refresh failed')).toBeInTheDocument();
    expect(screen.getByText('Network failed')).toBeInTheDocument();
  });

  it('does not show refresh error for rate_limit type', () => {
    render(
      <ProjectBoardErrorBanners
        {...noErrorProps}
        refreshError={{ type: 'rate_limit', message: 'Rate limited' }}
      />
    );
    expect(screen.queryByText('Refresh failed')).not.toBeInTheDocument();
  });

  it('shows projects error banner', () => {
    render(
      <ProjectBoardErrorBanners
        {...noErrorProps}
        projectsError={new Error('Failed to fetch')}
      />
    );
    expect(screen.getByText('Failed to load projects')).toBeInTheDocument();
  });

  it('shows board error with retry button', () => {
    const onRetryBoard = vi.fn();
    render(
      <ProjectBoardErrorBanners
        {...noErrorProps}
        boardError={new Error('Board fetch failed')}
        onRetryBoard={onRetryBoard}
      />
    );
    expect(screen.getByText('Failed to load board data')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry loading board data/i })).toBeInTheDocument();
  });

  it('does not show board error while loading', () => {
    render(
      <ProjectBoardErrorBanners
        {...noErrorProps}
        boardError={new Error('Board fetch failed')}
        boardLoading={true}
      />
    );
    expect(screen.queryByText('Failed to load board data')).not.toBeInTheDocument();
  });

  it('has no accessibility violations when showing rate limit', async () => {
    const { container } = render(
      <ProjectBoardErrorBanners {...noErrorProps} showRateLimitBanner={true} />
    );
    await expectNoA11yViolations(container);
  });

  it('has no accessibility violations when showing no errors', async () => {
    const { container } = render(<ProjectBoardErrorBanners {...noErrorProps} />);
    await expectNoA11yViolations(container);
  });
});
