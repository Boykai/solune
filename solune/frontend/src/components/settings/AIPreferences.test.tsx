/**
 * Tests for AIPreferences component.
 *
 * Covers: heading rendering, provider dropdown, model input,
 * temperature slider, temperature label with current value,
 * and user interactions that call setField.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@/test/test-utils';
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
  beforeEach(() => {
    mockSetField.mockClear();
  });

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

  it('calls setField when provider is changed', () => {
    render(<AIPreferences settings={defaultSettings} onSave={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('Provider'), { target: { value: 'azure_openai' } });
    expect(mockSetField).toHaveBeenCalledWith('provider', 'azure_openai');
  });

  it('calls setField when model input is changed', () => {
    render(<AIPreferences settings={defaultSettings} onSave={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'gpt-4' } });
    expect(mockSetField).toHaveBeenCalledWith('model', 'gpt-4');
  });

  it('calls setField when temperature slider is changed', () => {
    render(<AIPreferences settings={defaultSettings} onSave={vi.fn()} />);
    fireEvent.change(screen.getByRole('slider'), { target: { value: '1.2' } });
    expect(mockSetField).toHaveBeenCalledWith('temperature', 1.2);
  });
});
