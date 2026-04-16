/**
 * Display Settings component.
 *
 * Renders display preferences: dark/light theme toggle and rainbow theme toggle.
 */

import { useUserSettings } from '@/hooks/useSettings';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useRainbowTheme } from '@/hooks/useRainbowTheme';
import { SettingsSection } from './SettingsSection';

export function DisplaySettings() {
  const { updateSettings } = useUserSettings();
  const { isDarkMode, toggleTheme } = useAppTheme();
  const { isRainbow, toggleRainbow } = useRainbowTheme();

  const handleThemeSave = async () => {
    await updateSettings({
      display: { theme: isDarkMode ? 'dark' : 'light' },
    });
  };

  return (
    <SettingsSection
      title="Display"
      description="Customise the visual appearance of Solune."
      isDirty={false}
      hideSave
    >
      {/* Dark / Light toggle */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-sm font-medium text-foreground">Dark mode</span>
          <span className="text-xs text-muted-foreground">
            Switch between light and dark interface themes.
          </span>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={isDarkMode}
          onClick={async () => {
            toggleTheme();
            await handleThemeSave().catch(() => {});
          }}
          className={[
            'celestial-focus relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full',
            'border-2 border-transparent transition-colors duration-200 ease-in-out',
            'focus-visible:outline-none',
            isDarkMode ? 'bg-primary' : 'bg-muted',
          ].join(' ')}
          aria-label={isDarkMode ? 'Disable dark mode' : 'Enable dark mode'}
        >
          <span
            className={[
              'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm',
              'transition duration-200 ease-in-out',
              isDarkMode ? 'translate-x-5' : 'translate-x-0',
            ].join(' ')}
          />
        </button>
      </div>

      {/* Rainbow theme toggle */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-sm font-medium text-foreground">Rainbow theme</span>
          <span className="text-xs text-muted-foreground">
            Apply a vibrant rainbow colour scheme to primary interface elements.
          </span>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={isRainbow}
          onClick={async () => {
            toggleRainbow();
            await updateSettings({ display: { rainbow_theme: !isRainbow } }).catch(() => {});
          }}
          className={[
            'celestial-focus relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full',
            'border-2 border-transparent transition-colors duration-200 ease-in-out',
            'focus-visible:outline-none',
            isRainbow
              ? 'bg-gradient-to-r from-red-500 via-yellow-400 via-green-500 via-blue-500 to-violet-500'
              : 'bg-muted',
          ].join(' ')}
          aria-label={isRainbow ? 'Disable rainbow theme' : 'Enable rainbow theme'}
          title={isRainbow ? 'Disable rainbow theme' : 'Enable rainbow theme'}
        >
          <span
            className={[
              'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm',
              'transition duration-200 ease-in-out',
              isRainbow ? 'translate-x-5' : 'translate-x-0',
            ].join(' ')}
          />
        </button>
      </div>

      {isRainbow && (
        <p className="text-xs text-muted-foreground italic">
          🌈 Rainbow theme is active. Primary buttons, headers, and accent colours now cycle
          through the full spectrum.
        </p>
      )}
    </SettingsSection>
  );
}
