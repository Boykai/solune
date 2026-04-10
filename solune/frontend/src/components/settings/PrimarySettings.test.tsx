/**
 * Tests for PrimarySettings component.
 *
 * Covers: AI Configuration heading, provider selector, temperature slider,
 * Signal Connection section, and Chat/Agent Model dropdowns.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { PrimarySettings } from './PrimarySettings';

const mockSetField = vi.fn();
vi.mock('@/hooks/useSettingsForm', () => ({
  useSettingsForm: vi.fn(() => ({
    localState: {
      provider: 'copilot',
      model: 'gpt-4o',
      agent_model: '',
      temperature: 0.7,
      reasoning_effort: null,
      agent_reasoning_effort: null,
    },
    setField: mockSetField,
    isDirty: false,
  })),
}));
vi.mock('@/hooks/useSettings', () => ({
  useModelOptions: vi.fn(() => ({ data: null, isLoading: false, refetch: vi.fn() })),
}));
vi.mock('./SignalConnection', () => ({
  SignalConnection: () => <div data-testid="signal-connection">Signal Connection</div>,
}));
vi.mock('./DynamicDropdown', () => ({
  DynamicDropdown: (props: Record<string, unknown>) => (
    <div data-testid={props.id as string}>{props.label as string}</div>
  ),
}));

const defaultSettings = {
  provider: 'copilot' as const,
  model: 'gpt-4o',
  agent_model: '',
  temperature: 0.7,
  reasoning_effort: undefined,
  agent_reasoning_effort: undefined,
};

describe('PrimarySettings', () => {
  it('renders AI Configuration heading', () => {
    render(<PrimarySettings settings={defaultSettings} onSave={vi.fn()} />);
    expect(screen.getByRole('heading', { name: 'AI Configuration' })).toBeInTheDocument();
  });

  it('shows provider selector with options', () => {
    render(<PrimarySettings settings={defaultSettings} onSave={vi.fn()} />);
    const select = screen.getByLabelText('Model Provider') as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    expect(select.value).toBe('copilot');

    const options = Array.from(select.options).map((o) => o.textContent);
    expect(options).toContain('GitHub Copilot');
    expect(options).toContain('Azure OpenAI');
  });

  it('shows temperature slider', () => {
    render(<PrimarySettings settings={defaultSettings} onSave={vi.fn()} />);
    const slider = screen.getByRole('slider') as HTMLInputElement;
    expect(slider).toBeInTheDocument();
    expect(slider.value).toBe('0.7');
  });

  it('renders Signal Connection section', () => {
    render(<PrimarySettings settings={defaultSettings} onSave={vi.fn()} />);
    expect(screen.getByTestId('signal-connection')).toBeInTheDocument();
  });

  it('renders Chat Model and Agent Model dropdowns', () => {
    render(<PrimarySettings settings={defaultSettings} onSave={vi.fn()} />);
    expect(screen.getByTestId('primary-chat-model')).toBeInTheDocument();
    expect(screen.getByText('Chat Model')).toBeInTheDocument();
    expect(screen.getByTestId('primary-agent-model')).toBeInTheDocument();
    expect(screen.getByText('Agent Model (Auto)')).toBeInTheDocument();
  });
});
