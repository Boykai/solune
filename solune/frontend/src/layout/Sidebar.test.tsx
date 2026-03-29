import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@/components/ui/tooltip';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from './Sidebar';

const defaultProps = {
  isCollapsed: false,
  onToggle: vi.fn(),
  isDarkMode: false,
  onToggleTheme: vi.fn(),
  recentInteractions: [],
  projects: [],
  projectsLoading: false,
  onSelectProject: vi.fn(),
};

function renderSidebar(overrides = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <TooltipProvider delayDuration={0}>
        <MemoryRouter>
          <Sidebar {...defaultProps} {...overrides} />
        </MemoryRouter>
      </TooltipProvider>
    </QueryClientProvider>,
  );
}

describe('Sidebar', () => {
  it('renders brand text when expanded', () => {
    renderSidebar();
    expect(screen.getByText('Solune')).toBeInTheDocument();
  });

  it('hides brand text when collapsed', () => {
    renderSidebar({ isCollapsed: true });
    expect(screen.queryByText('Solune')).not.toBeInTheDocument();
  });

  it('renders navigation links', () => {
    renderSidebar();
    // NAV_ROUTES should provide at least a few labeled routes
    const links = screen.getAllByRole('link');
    expect(links.length).toBeGreaterThan(0);
  });

  it('calls onToggle when collapse button is clicked', () => {
    const onToggle = vi.fn();
    renderSidebar({ onToggle });
    const btn = screen.getByRole('button', { name: /collapse sidebar/i });
    fireEvent.click(btn);
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it('calls onToggleTheme when theme button is clicked', () => {
    const onToggleTheme = vi.fn();
    renderSidebar({ onToggleTheme });
    const btn = screen.getByRole('button', { name: /switch to dark mode/i });
    fireEvent.click(btn);
    expect(onToggleTheme).toHaveBeenCalledOnce();
  });

  it('shows moon icon in dark mode', () => {
    renderSidebar({ isDarkMode: true });
    expect(screen.getByRole('button', { name: /switch to light mode/i })).toBeInTheDocument();
  });

  it('shows project initial when project selected', () => {
    renderSidebar({
      selectedProject: { project_id: 'PVT_1', name: 'MyProject', owner_login: 'octo' },
    });
    expect(screen.getByText('M')).toBeInTheDocument();
    expect(screen.getByText('MyProject')).toBeInTheDocument();
  });

  it('shows placeholder when no project selected', () => {
    renderSidebar();
    expect(screen.getByText('Select project')).toBeInTheDocument();
    expect(screen.getByText('?')).toBeInTheDocument();
  });

  it('renders mobile overlay when isMobile and expanded', () => {
    renderSidebar({ isMobile: true, isCollapsed: false });
    expect(screen.getByRole('presentation')).toBeInTheDocument();
  });

  it('does not render overlay when isMobile and collapsed', () => {
    renderSidebar({ isMobile: true, isCollapsed: true });
    expect(screen.queryByRole('presentation')).not.toBeInTheDocument();
  });

  it('shows recent interactions when expanded', () => {
    renderSidebar({
      recentInteractions: [
        {
          item_id: 'i-1',
          title: 'Fix auth bug',
          status: 'Todo',
          statusColor: 'GREEN',
          number: 42,
        },
      ],
    });
    expect(screen.getByText('Fix auth bug')).toBeInTheDocument();
    expect(screen.getByText('#42')).toBeInTheDocument();
  });

  it('shows empty message when no recent interactions', () => {
    renderSidebar({ recentInteractions: [] });
    expect(screen.getByText(/no recent parent issues/i)).toBeInTheDocument();
  });
});
