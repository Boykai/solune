import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { expectNoA11yViolations } from '@/test/a11y-helpers';
import { SettingsPage } from './SettingsPage';

vi.mock('@/hooks/useSettings', () => ({
  useUserSettings: () => ({
    settings: undefined,
    isLoading: false,
    error: null,
    updateSettings: vi.fn(),
    isUpdating: false,
  }),
}));

describe('SettingsPage', () => {
  it('renders the settings heading', () => {
    render(<SettingsPage />);
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('does not render AdvancedSettings', () => {
    render(<SettingsPage />);
    expect(screen.queryByText('Advanced Settings')).not.toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<SettingsPage />);
    await expectNoA11yViolations(container);
  });
});
