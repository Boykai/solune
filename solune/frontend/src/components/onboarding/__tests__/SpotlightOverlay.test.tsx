import { describe, it, expect } from 'vitest';
import { render } from '@/test/test-utils';
import { SpotlightOverlay } from '../SpotlightOverlay';

describe('SpotlightOverlay', () => {
  it('returns null when not visible', () => {
    const { container } = render(
      <SpotlightOverlay targetRect={null} isVisible={false} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders overlay when visible', () => {
    const { container } = render(
      <SpotlightOverlay targetRect={null} isVisible={true} />
    );
    expect(container.firstChild).toBeTruthy();
  });

  it('has aria-hidden on the overlay', () => {
    const { container } = render(
      <SpotlightOverlay targetRect={null} isVisible={true} />
    );
    const overlay = container.firstChild as HTMLElement;
    expect(overlay?.getAttribute('aria-hidden')).toBe('true');
  });

  it('applies clip-path when targetRect is provided', () => {
    const rect = new DOMRect(100, 50, 200, 150);
    const { container } = render(
      <SpotlightOverlay targetRect={rect} isVisible={true} />
    );
    const overlay = container.firstChild as HTMLElement;
    expect(overlay?.style.clipPath).toContain('polygon');
  });

  it('does not set clip-path when targetRect is null', () => {
    const { container } = render(
      <SpotlightOverlay targetRect={null} isVisible={true} />
    );
    const overlay = container.firstChild as HTMLElement;
    expect(overlay?.style.clipPath).toBeFalsy();
  });

  it('uses fixed positioning for full viewport coverage', () => {
    const { container } = render(
      <SpotlightOverlay targetRect={null} isVisible={true} />
    );
    const overlay = container.firstChild as HTMLElement;
    expect(overlay?.className).toContain('fixed');
    expect(overlay?.className).toContain('inset-0');
  });
});
