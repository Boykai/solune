import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BuildProgress } from './BuildProgress';
import type { BuildProgressPayload } from '@/types/app-template';

function makePayload(overrides: Partial<BuildProgressPayload> = {}): BuildProgressPayload {
  return {
    type: 'build_progress',
    app_name: 'my-app',
    phase: 'scaffolding',
    agent_name: null,
    detail: '',
    pct_complete: 0,
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

describe('BuildProgress', () => {
  it('renders nothing when progress is null', () => {
    const { container } = render(<BuildProgress progress={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders app name in heading', () => {
    render(<BuildProgress progress={makePayload()} />);
    expect(screen.getByText(/Build Progress — my-app/)).toBeInTheDocument();
  });

  it('renders percentage', () => {
    render(<BuildProgress progress={makePayload({ pct_complete: 42 })} />);
    expect(screen.getByText('42%')).toBeInTheDocument();
  });

  it('renders all phase labels', () => {
    render(<BuildProgress progress={makePayload()} />);
    expect(screen.getByText('Scaffolding')).toBeInTheDocument();
    expect(screen.getByText('Configuring Pipeline')).toBeInTheDocument();
    expect(screen.getByText('Creating Issue')).toBeInTheDocument();
    expect(screen.getByText('Building')).toBeInTheDocument();
    expect(screen.getByText('Deploy Preparation')).toBeInTheDocument();
    expect(screen.getByText('Complete')).toBeInTheDocument();
  });

  it('shows detail text for current phase', () => {
    render(
      <BuildProgress
        progress={makePayload({ phase: 'building', detail: 'Compiling TypeScript...' })}
      />,
    );
    expect(screen.getByText('Compiling TypeScript...')).toBeInTheDocument();
  });

  it('shows agent name for current phase', () => {
    render(
      <BuildProgress
        progress={makePayload({ phase: 'building', agent_name: 'code-builder' })}
      />,
    );
    expect(screen.getByText('Agent: code-builder')).toBeInTheDocument();
  });

  it('does not show detail for non-current phases', () => {
    render(
      <BuildProgress
        progress={makePayload({ phase: 'building', detail: 'Current detail' })}
      />,
    );
    // There should be exactly one detail text
    expect(screen.getAllByText('Current detail')).toHaveLength(1);
  });

  it('renders checkmark for completed phases', () => {
    render(
      <BuildProgress
        progress={makePayload({ phase: 'building', pct_complete: 50 })}
      />,
    );
    // First three phases should show checkmarks
    const checkmarks = screen.getAllByText('✓');
    expect(checkmarks.length).toBe(3); // scaffolding, configuring, issuing
  });

  it('renders progress bar with correct width', () => {
    const { container } = render(
      <BuildProgress progress={makePayload({ pct_complete: 75 })} />,
    );
    const progressBar = container.querySelector('[style*="width: 75%"]');
    expect(progressBar).toBeInTheDocument();
  });

  it('handles failed phase', () => {
    render(
      <BuildProgress
        progress={makePayload({ phase: 'failed', pct_complete: 50 })}
      />,
    );
    // Progress bar should use red color for failed
    const { container } = render(
      <BuildProgress
        progress={makePayload({ phase: 'failed', pct_complete: 50 })}
      />,
    );
    const bar = container.querySelector('.bg-red-500');
    expect(bar).toBeInTheDocument();
  });

  it('renders complete phase correctly', () => {
    render(
      <BuildProgress
        progress={makePayload({ phase: 'complete', pct_complete: 100 })}
      />,
    );
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <BuildProgress progress={makePayload()} className="custom-class" />,
    );
    expect(container.firstChild).toHaveClass('custom-class');
  });
});
