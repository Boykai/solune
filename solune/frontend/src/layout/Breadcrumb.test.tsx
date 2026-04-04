import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Breadcrumb } from './Breadcrumb';

// Mock hooks and utils
vi.mock('@/hooks/useBreadcrumb', () => ({
  useBreadcrumbLabels: () => ({}),
}));

vi.mock('@/lib/breadcrumb-utils', () => ({
  buildBreadcrumbSegments: vi.fn().mockReturnValue([
    { path: '/', label: 'Home' },
    { path: '/projects', label: 'Projects' },
  ]),
}));

function renderBreadcrumb(path = '/projects') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Breadcrumb />
    </MemoryRouter>,
  );
}

describe('Breadcrumb', () => {
  it('renders breadcrumb nav with aria-label', () => {
    renderBreadcrumb();
    expect(screen.getByRole('navigation', { name: /breadcrumb/i })).toBeInTheDocument();
  });

  it('renders segment labels', () => {
    renderBreadcrumb();
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Projects')).toBeInTheDocument();
  });

  it('first segment is a link', () => {
    renderBreadcrumb();
    const homeLink = screen.getByText('Home');
    expect(homeLink.closest('a')).toHaveAttribute('href', '/');
  });

  it('last segment is not a link', () => {
    renderBreadcrumb();
    const projectsLabel = screen.getByText('Projects');
    expect(projectsLabel.closest('a')).toBeNull();
  });

  it('last segment has font-medium class', () => {
    renderBreadcrumb();
    const projectsLabel = screen.getByText('Projects');
    expect(projectsLabel.className).toContain('font-medium');
  });
});
