import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RateLimitBar } from './RateLimitBar';

const mockUseRateLimitStatus = vi.fn();

vi.mock('@/context/RateLimitContext', () => ({
  useRateLimitStatus: () => mockUseRateLimitStatus(),
}));

vi.mock('@/utils/formatTime', () => ({
  formatTimeUntil: () => 'in 30 minutes',
}));

describe('RateLimitBar', () => {
  it('returns null when no info and no error', () => {
    mockUseRateLimitStatus.mockReturnValue({
      rateLimitState: { info: null, hasError: false },
    });
    const { container } = render(<RateLimitBar />);
    expect(container.firstChild).toBeNull();
  });

  it('renders rate limit info when available', () => {
    mockUseRateLimitStatus.mockReturnValue({
      rateLimitState: {
        info: { limit: 5000, remaining: 4500, reset_at: Date.now() / 1000 + 1800, used: 500 },
        hasError: false,
      },
    });
    render(<RateLimitBar />);
    expect(screen.getByText('4500/5000 remaining')).toBeInTheDocument();
    expect(screen.getByText('GitHub API')).toBeInTheDocument();
  });

  it('renders error state when rate limited', () => {
    mockUseRateLimitStatus.mockReturnValue({
      rateLimitState: { info: null, hasError: true },
    });
    render(<RateLimitBar />);
    expect(screen.getByText('Limit reached')).toBeInTheDocument();
  });

  it('has aria-label for accessibility', () => {
    mockUseRateLimitStatus.mockReturnValue({
      rateLimitState: {
        info: { limit: 5000, remaining: 4500, reset_at: Date.now() / 1000 + 1800, used: 500 },
        hasError: false,
      },
    });
    render(<RateLimitBar />);
    expect(screen.getByLabelText('GitHub API rate limit')).toBeInTheDocument();
  });

  it('shows tooltip with usage details', () => {
    mockUseRateLimitStatus.mockReturnValue({
      rateLimitState: {
        info: { limit: 5000, remaining: 4500, reset_at: Date.now() / 1000 + 1800, used: 500 },
        hasError: false,
      },
    });
    render(<RateLimitBar />);
    const bar = screen.getByLabelText('GitHub API rate limit');
    expect(bar.getAttribute('title')).toContain('500/5000 used');
  });

  it('shows error tooltip when rate limited', () => {
    mockUseRateLimitStatus.mockReturnValue({
      rateLimitState: { info: null, hasError: true },
    });
    render(<RateLimitBar />);
    const bar = screen.getByLabelText('GitHub API rate limit');
    expect(bar.getAttribute('title')).toContain('rate limit reached');
  });
});
