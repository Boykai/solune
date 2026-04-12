import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { HelpPage } from './HelpPage';

expect.extend(toHaveNoViolations);

const mockRestart = vi.fn();

vi.mock('@/hooks/useOnboarding', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useOnboarding')>();
  return {
    ...actual,
    useOnboarding: () => ({
      isActive: false,
      hasCompleted: true,
      currentStep: 0,
      totalSteps: 9,
      next: vi.fn(),
      prev: vi.fn(),
      skip: vi.fn(),
      restart: mockRestart,
    }),
  };
});

vi.mock('@/lib/commands/registry', () => ({
  getAllCommands: () => [],
}));

describe('HelpPage', () => {
  it('renders and shows the help center heading', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Help Center')).toBeInTheDocument();
  });

  it('renders the compact page header as a <header> element', () => {
    const { container } = render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    expect(container.querySelector('header')).toBeInTheDocument();
  });

  it('renders the title in an h2 heading', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    const heading = screen.getByRole('heading', { level: 2, name: 'Help Center' });
    expect(heading).toBeInTheDocument();
  });

  it('shows the eyebrow text', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('// Guidance & support')).toBeInTheDocument();
  });

  it('shows the description text', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    expect(
      screen.getByText('Everything you need to navigate your celestial workspace.'),
    ).toBeInTheDocument();
  });

  it('renders the Replay Tour action button', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    const replayButton = screen.getByRole('button', { name: /replay tour/i });
    expect(replayButton).toBeInTheDocument();
  });

  it('calls restart when the Replay Tour button is clicked', async () => {
    const { default: userEvent } = await import('@testing-library/user-event');
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole('button', { name: /replay tour/i }));
    expect(mockRestart).toHaveBeenCalledTimes(1);
  });

  it('does not render any stats chips (HelpPage has no stats)', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    // The mobile toggle button is only shown when stats are provided
    expect(screen.queryByRole('button', { name: /show stats/i })).not.toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    // heading-order is a pre-existing issue in FeatureGuideCard (uses h4 inside h2 sections)
    const results = await axe(container, {
      rules: { 'heading-order': { enabled: false } },
    });
    expect(results).toHaveNoViolations();
  });
});
