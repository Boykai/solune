/**
 * Settings page layout.
 *
 * Displays primary settings (AI configuration, Signal connection).
 * Includes unsaved changes warning (FR-037).
 */

import { useEffect, useCallback } from 'react';
import { Play } from '@/lib/icons';
import { Button } from '@/components/ui/button';
import { CelestialLoadingProgress } from '@/components/common/CelestialLoadingProgress';
import { PrimarySettings } from '@/components/settings/PrimarySettings';
import { DisplaySettings } from '@/components/settings/DisplaySettings';
import { useUserSettings } from '@/hooks/useSettings';
import { useOnboarding } from '@/hooks/useOnboarding';
import type { UserPreferencesUpdate } from '@/types';

/**
 * Hook to warn user about unsaved changes when navigating away.
 * Attaches `beforeunload` listener when any section reports dirty state.
 */
function useUnsavedChangesWarning(isDirty: boolean) {
  const handleBeforeUnload = useCallback(
    (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
      }
    },
    [isDirty]
  );

  useEffect(() => {
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [handleBeforeUnload]);
}

export function SettingsPage() {
  const { restart } = useOnboarding();
  const {
    settings: userSettings,
    isLoading: userLoading,
    updateSettings: updateUserSettings,
    isUpdating: isUserUpdating,
  } = useUserSettings();

  // Track whether any mutation is in-flight as proxy for dirty state
  // (Individual dirty tracking is handled within each SettingsSection)
  useUnsavedChangesWarning(isUserUpdating);

  const handleUserSave = async (update: UserPreferencesUpdate) => {
    await updateUserSettings(update);
  };

  if (userLoading) {
    return (
      <div className="mx-auto flex w-full max-w-4xl flex-col p-4 md:p-8">
        <div className="flex flex-col items-center justify-center flex-1 gap-4">
          <CelestialLoadingProgress
            phases={[
              { label: 'Loading user settings…', complete: !userLoading },
            ]}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="celestial-fade-in mx-auto flex w-full max-w-4xl flex-col rounded-[1.75rem] border border-border/70 bg-background/42 p-4 backdrop-blur-sm md:p-8">
      <div className="mb-8">
        <p className="mb-1 text-xs uppercase tracking-[0.24em] text-primary/80">
          Orbital Configuration
        </p>
        <h2 className="mb-2 text-3xl font-display font-medium tracking-[0.04em]">Settings</h2>
        <div className="flex items-center gap-4">
          <p className="text-muted-foreground">Configure your preferences for Solune.</p>
          <Button onClick={restart} variant="outline" size="sm" className="shrink-0">
            <Play className="mr-2 h-4 w-4" />
            Replay Tour
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-8">
        {/* Display Settings: Dark mode + Rainbow theme */}
        <DisplaySettings />

        {/* Primary Settings: AI Configuration + Signal Connection */}
        {userSettings && <PrimarySettings settings={userSettings.ai} onSave={handleUserSave} />}
      </div>
    </div>
  );
}
