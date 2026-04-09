import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { TourProgress } from '../TourProgress';

describe('TourProgress', () => {
  it('renders the correct number of dots', () => {
    render(<TourProgress currentStep={0} totalSteps={5} />);
    const group = screen.getByRole('group');
    // Each dot is a <span> child inside the group
    const dots = group.querySelectorAll('span');
    expect(dots).toHaveLength(5);
  });

  it('has accessible aria-label with step info', () => {
    render(<TourProgress currentStep={2} totalSteps={5} />);
    const group = screen.getByRole('group');
    expect(group).toHaveAttribute('aria-label', 'Step 3 of 5');
  });

  it('marks current step dot with scale-125 class', () => {
    render(<TourProgress currentStep={1} totalSteps={3} />);
    const group = screen.getByRole('group');
    const dots = group.querySelectorAll('span');
    expect(dots[1]?.className).toContain('scale-125');
    expect(dots[0]?.className).not.toContain('scale-125');
    expect(dots[2]?.className).not.toContain('scale-125');
  });

  it('marks completed steps with bg-primary/80', () => {
    render(<TourProgress currentStep={2} totalSteps={4} />);
    const group = screen.getByRole('group');
    const dots = group.querySelectorAll('span');
    // Steps 0 and 1 are completed (< currentStep)
    expect(dots[0]?.className).toContain('bg-primary/80');
    expect(dots[1]?.className).toContain('bg-primary/80');
  });

  it('marks upcoming steps with border styling', () => {
    render(<TourProgress currentStep={0} totalSteps={3} />);
    const group = screen.getByRole('group');
    const dots = group.querySelectorAll('span');
    // Steps 1 and 2 are upcoming (> currentStep)
    expect(dots[1]?.className).toContain('border');
    expect(dots[2]?.className).toContain('border');
  });

  it('handles single step tour', () => {
    render(<TourProgress currentStep={0} totalSteps={1} />);
    const group = screen.getByRole('group');
    const dots = group.querySelectorAll('span');
    expect(dots).toHaveLength(1);
    expect(dots[0]?.className).toContain('scale-125');
  });

  it('uses aria-hidden on dots', () => {
    render(<TourProgress currentStep={0} totalSteps={2} />);
    const group = screen.getByRole('group');
    const dots = group.querySelectorAll('span');
    for (const dot of dots) {
      expect(dot.getAttribute('aria-hidden')).toBe('true');
    }
  });
});
