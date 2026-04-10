/**
 * Tests for AIPreferences component.
 *
 * Covers: heading rendering, provider dropdown, model input,
 * temperature slider, and temperature label with current value.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { AIPreferences } from './AIPreferences';

const mockSetField = vi.fn();
vi.mock('@/hooks/useSettingsForm', () => ({
  useSettingsForm: vi.fn(() => ({
    localState: { provider: 'copilot', model: 'gpt-4o', temperature: 0.7 },
    setField: mockSetField,
    isDirty: false,
  })),
}));

const defaultSettings = { provider: 'copilot' as const, model: 'gpt-4o', temperature: 0.7, agent_model: '' };

describe('AIPreferences', () => {
  it('renders AI Preferences heading', () => {
    render(<AIPreferences settings={defaultSettings} onSave={vi.fn()} />);
    expect(screen.getByRole('heading', { name: 'AI Preferences' })).toBeInTheDocument();
  });

  it('shows provider dropdown with options', () => {
    render(<AIPreferences settings={defaultSettings} onSave={vi.fn()} />);
    const select = screen.getByLabelText('Provider') as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    expect(select.value).toBe('copilot');

    const options = Array.from(select.options).map((o) => o.value);
    expect(options).toContain('copilot');
    expect(options).toContain('azure_openai');
  });

  it('shows model input', () => {
    render(<AIPreferences settings={defaultSettings} onSave={vi.fn()} />);
    const input = screen.getByLabelText('Model') as HTMLInputElement;
    expect(input).toBeInTheDocument();
    expect(input.value).toBe('gpt-4o');
  });

  it('shows temperature slider', () => {
    render(<AIPreferences settings={defaultSettings} onSave={vi.fn()} />);
    const slider = screen.getByRole('slider') as HTMLInputElement;
    expect(slider).toBeInTheDocument();
    expect(slider.value).toBe('0.7');
  });

  it('shows temperature label with current value', () => {
    render(<AIPreferences settings={defaultSettings} onSave={vi.fn()} />);
    expect(screen.getByText('Temperature: 0.7')).toBeInTheDocument();
  });
});
