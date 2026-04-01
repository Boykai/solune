/**
 * BuildProgressCard — compact inline card for chat messages showing build progress.
 * Displays current phase, active agent, progress bar, and detail text.
 */

import { cn } from '@/lib/utils';
import type { BuildPhase, BuildProgressPayload, BuildCompletePayload } from '@/types/app-template';

const PHASE_LABELS: Record<BuildPhase, string> = {
  scaffolding: 'Scaffolding',
  configuring: 'Configuring',
  issuing: 'Creating Issue',
  building: 'Building',
  deploying_prep: 'Preparing Deploy',
  complete: 'Complete',
  failed: 'Failed',
};

const PHASE_COLORS: Record<BuildPhase, string> = {
  scaffolding: 'bg-blue-500',
  configuring: 'bg-indigo-500',
  issuing: 'bg-violet-500',
  building: 'bg-amber-500',
  deploying_prep: 'bg-cyan-500',
  complete: 'bg-emerald-500',
  failed: 'bg-red-500',
};

interface BuildProgressCardProps {
  progress: BuildProgressPayload;
  completion?: BuildCompletePayload | null;
}

export function BuildProgressCard({ progress, completion }: BuildProgressCardProps) {
  const isComplete = progress.phase === 'complete';
  const isFailed = progress.phase === 'failed';

  return (
    <div
      className={cn(
        'rounded-lg border p-4',
        isComplete && 'border-emerald-200 bg-emerald-50/50 dark:border-emerald-800 dark:bg-emerald-950/20',
        isFailed && 'border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-950/20',
        !isComplete && !isFailed && 'border-border bg-card/80',
      )}
      data-testid="build-progress-card"
    >
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">🏗️ {progress.app_name}</span>
          <span className="rounded-full bg-muted/60 px-2 py-0.5 text-xs font-medium">
            {PHASE_LABELS[progress.phase]}
          </span>
        </div>
        <span className="text-xs text-muted-foreground">{progress.pct_complete}%</span>
      </div>

      {/* Progress bar */}
      <div className="mb-2 h-1.5 overflow-hidden rounded-full bg-muted/40">
        <div
          className={cn('h-full rounded-full transition-all duration-500', PHASE_COLORS[progress.phase])}
          style={{ width: `${progress.pct_complete}%` }}
        />
      </div>

      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">{progress.detail}</p>
        {progress.agent_name && (
          <span className="rounded bg-muted/60 px-1.5 py-0.5 text-xs text-muted-foreground">
            {progress.agent_name}
          </span>
        )}
      </div>

      {/* Completion links */}
      {completion && (
        <div className="mt-3 border-t border-border/50 pt-3">
          <p className="mb-2 text-sm font-medium text-emerald-600 dark:text-emerald-400">
            {completion.message}
          </p>
          <div className="flex flex-wrap gap-2">
            {completion.links.app_url && (
              <a
                href={completion.links.app_url}
                className="rounded bg-muted/60 px-2 py-1 text-xs text-primary hover:underline"
              >
                View App
              </a>
            )}
            {completion.links.repo_url && (
              <a
                href={completion.links.repo_url}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded bg-muted/60 px-2 py-1 text-xs text-primary hover:underline"
              >
                Repository
              </a>
            )}
            {completion.links.issue_url && (
              <a
                href={completion.links.issue_url}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded bg-muted/60 px-2 py-1 text-xs text-primary hover:underline"
              >
                Issue
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
