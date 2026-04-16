/**
 * PresetBadge — visual indicator for system preset pipelines.
 * Shows a lock icon with the preset name in accent colors.
 */

import { Lock } from '@/lib/icons';
import { cn } from '@/lib/utils';

interface PresetBadgeProps {
  presetId: string;
  className?: string;
}

const PRESET_STYLES: Record<string, { label: string; classes: string }> = {
  'github': {
    label: 'GitHub',
    classes: 'solar-chip-success',
  },
  'spec-kit': {
    label: 'Spec Kit',
    classes: 'solar-chip-violet',
  },
  'default': {
    label: 'Default',
    classes: 'solar-chip-soft',
  },
  'app-builder': {
    label: 'App Builder',
    classes: 'solar-chip-neutral',
  },
};

export function PresetBadge({ presetId, className = '' }: PresetBadgeProps) {
  const style = PRESET_STYLES[presetId] ?? {
    label: presetId,
    classes: 'solar-chip-soft',
  };

  return (
    <span
      className={cn('inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em]', style.classes, className)}
    >
      <Lock className="h-2.5 w-2.5" />
      {style.label}
    </span>
  );
}
