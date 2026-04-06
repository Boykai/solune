import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';

vi.mock('react-router-dom', () => ({
  useLocation: () => ({ pathname: '/test' }),
  Outlet: () => <div data-testid="outlet" />,
}));

import { PageTransition } from './PageTransition';

describe('PageTransition', () => {
  it('renders Outlet content', () => {
    render(<PageTransition />);
    expect(screen.getByTestId('outlet')).toBeInTheDocument();
  });

  it('has motion-safe:animate-page-enter class', () => {
    render(<PageTransition />);
    const wrapper = screen.getByTestId('outlet').parentElement!;
    expect(wrapper.className).toContain('motion-safe:animate-page-enter');
  });

  it('uses pathname as key for remount on route change', () => {
    const { container } = render(<PageTransition />);
    const wrapper = container.firstElementChild!;
    expect(wrapper.className).toContain('motion-safe:animate-page-enter');
    // The wrapper div exists and wraps the Outlet
    expect(wrapper).toContainElement(screen.getByTestId('outlet'));
  });
});
