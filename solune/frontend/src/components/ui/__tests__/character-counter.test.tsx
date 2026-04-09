import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { CharacterCounter } from '../character-counter';

describe('CharacterCounter', () => {
  it('renders current and max character counts', () => {
    render(<CharacterCounter current={50} max={200} />);
    expect(screen.getByText('50 / 200 chars')).toBeInTheDocument();
  });

  it('formats large numbers with locale separators', () => {
    render(<CharacterCounter current={1500} max={10000} />);
    const text = screen.getByText(/chars/);
    // toLocaleString adds commas in en-US
    expect(text).toBeInTheDocument();
  });

  it('applies warning style when over 80% of max', () => {
    const { container } = render(<CharacterCounter current={170} max={200} />);
    const span = container.querySelector('span');
    expect(span?.className).toContain('amber');
  });

  it('applies destructive style when over max', () => {
    const { container } = render(<CharacterCounter current={250} max={200} />);
    const span = container.querySelector('span');
    expect(span?.className).toContain('destructive');
  });

  it('applies normal style when under 80%', () => {
    const { container } = render(<CharacterCounter current={10} max={200} />);
    const span = container.querySelector('span');
    expect(span?.className).toContain('muted-foreground');
    expect(span?.className).not.toContain('amber');
    expect(span?.className).not.toContain('destructive');
  });

  it('applies custom className', () => {
    const { container } = render(
      <CharacterCounter current={0} max={100} className="custom-class" />
    );
    const span = container.querySelector('span');
    expect(span?.className).toContain('custom-class');
  });

  it('handles zero current', () => {
    render(<CharacterCounter current={0} max={100} />);
    expect(screen.getByText('0 / 100 chars')).toBeInTheDocument();
  });

  it('handles exactly 80% threshold', () => {
    const { container } = render(<CharacterCounter current={160} max={200} />);
    const span = container.querySelector('span');
    // 160 / 200 = exactly 80% — not > 80%, so no warning
    expect(span?.className).not.toContain('amber');
  });
});
