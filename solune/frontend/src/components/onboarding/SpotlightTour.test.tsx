import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';
import { SpotlightTour } from './SpotlightTour';

const onboardingState = {
  isActive: true,
  currentStep: 0,
  totalSteps: 14,
  next: vi.fn(),
  prev: vi.fn(),
  skip: vi.fn(),
};

vi.mock('@/hooks/useOnboarding', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useOnboarding')>();
  return {
    ...actual,
    useOnboarding: () => onboardingState,
  };
});

describe('SpotlightTour', () => {
  const originalScrollTo = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollTo');

  beforeEach(() => {
    onboardingState.isActive = true;
    onboardingState.currentStep = 0;
    onboardingState.totalSteps = 14;
    onboardingState.next.mockReset();
    onboardingState.prev.mockReset();
    onboardingState.skip.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
    if (originalScrollTo) {
      Object.defineProperty(HTMLElement.prototype, 'scrollTo', originalScrollTo);
      return;
    }

    Reflect.deleteProperty(HTMLElement.prototype, 'scrollTo');
  });

  it('renders the first tour step', () => {
    render(
      <SpotlightTour isSidebarCollapsed={false} onToggleSidebar={vi.fn()} />,
    );
    expect(screen.getByText('Welcome to Solune')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <SpotlightTour isSidebarCollapsed={false} onToggleSidebar={vi.fn()} />,
    );
    await expectNoA11yViolations(container);
  });

  it('scrolls the nearest scrollable surface instead of the shell container', () => {
    vi.useFakeTimers();

    const scrollTo = vi.fn(function scrollTo(
      this: HTMLElement,
      options?: number | ScrollToOptions,
    ) {
      if (typeof options === 'number') {
        this.scrollTop = options;
        return;
      }

      if (options?.top != null) {
        this.scrollTop = options.top;
      }
    });

    Object.defineProperty(HTMLElement.prototype, 'scrollTo', {
      configurable: true,
      value: scrollTo,
    });

    const view = render(
      <div className="celestial-shell" style={{ overflow: 'hidden', height: '200px' }}>
        <div data-testid="sidebar-scroll-surface" style={{ overflowY: 'auto', maxHeight: '100px' }}>
          <div style={{ height: '160px' }} />
          <div data-tour-step="sidebar-nav">Sidebar target</div>
        </div>
        <SpotlightTour isSidebarCollapsed={false} onToggleSidebar={vi.fn()} />
      </div>,
    );

    const shell = document.querySelector('.celestial-shell') as HTMLDivElement;
    const scrollSurface = screen.getByTestId('sidebar-scroll-surface') as HTMLDivElement;
    const target = screen.getByText('Sidebar target');

    Object.defineProperty(shell, 'scrollHeight', { configurable: true, value: 400 });
    Object.defineProperty(shell, 'clientHeight', { configurable: true, value: 200 });
    shell.scrollTop = 120;

    Object.defineProperty(scrollSurface, 'scrollHeight', { configurable: true, value: 400 });
    Object.defineProperty(scrollSurface, 'clientHeight', { configurable: true, value: 100 });
    scrollSurface.scrollTop = 0;

    vi.spyOn(scrollSurface, 'getBoundingClientRect').mockReturnValue(
      DOMRect.fromRect({ x: 0, y: 0, width: 240, height: 100 }),
    );
    vi.spyOn(target, 'getBoundingClientRect').mockReturnValue(
      DOMRect.fromRect({ x: 0, y: 160, width: 200, height: 24 }),
    );

    onboardingState.currentStep = 1;
    view.rerender(
      <div className="celestial-shell" style={{ overflow: 'hidden', height: '200px' }}>
        <div data-testid="sidebar-scroll-surface" style={{ overflowY: 'auto', maxHeight: '100px' }}>
          <div style={{ height: '160px' }} />
          <div data-tour-step="sidebar-nav">Sidebar target</div>
        </div>
        <SpotlightTour isSidebarCollapsed={false} onToggleSidebar={vi.fn()} />
      </div>,
    );

    act(() => {
      vi.runAllTimers();
    });

    expect(shell.scrollTop).toBe(0);
    expect(scrollSurface.scrollTop).toBeGreaterThan(0);
  });
});
