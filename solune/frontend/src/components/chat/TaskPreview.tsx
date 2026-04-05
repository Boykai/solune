/**
 * Task preview component for AI-generated task proposals.
 */

import { memo } from 'react';
import type { AITaskProposal } from '@/types';
import { GitBranch } from '@/lib/icons';
import { useCountdown, formatCountdown } from '@/hooks/useCountdown';
import { cn } from '@/lib/utils';

interface TaskPreviewProps {
  proposal: AITaskProposal;
  onConfirm: () => void;
  onReject: () => void;
}

function getPipelineLabel(proposal: AITaskProposal): string | null {
  if (proposal.status !== 'confirmed') return null;
  if (proposal.pipeline_name) return proposal.pipeline_name;
  if (proposal.pipeline_source === 'user') return 'Custom Mappings';
  if (proposal.pipeline_source === 'default') return 'Default';
  return null;
}

export const TaskPreview = memo(function TaskPreview({ proposal, onConfirm, onReject }: TaskPreviewProps) {
  const pipelineLabel = getPipelineLabel(proposal);
  const remaining = useCountdown(proposal.expires_at);
  const isExpired = remaining <= 0;
  const isUrgent = remaining > 0 && remaining <= 60;

  return (
    <div className="ml-11 max-w-[90vw] self-start overflow-hidden rounded-lg border border-border bg-background/56 md:max-w-[500px]">
      <div className="bg-primary text-primary-foreground px-4 py-2 text-xs font-medium flex items-center justify-between">
        <span>Task Preview</span>
        <span
          className={cn(
            'tabular-nums',
            isExpired && 'text-destructive-foreground opacity-80',
            isUrgent && !isExpired && 'text-yellow-200',
          )}
          aria-live="polite"
        >
          {formatCountdown(remaining)}
        </span>
      </div>

      <div className="p-4">
        <h3 className="text-base font-semibold text-foreground mb-3">{proposal.proposed_title}</h3>

        <div className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
          {proposal.proposed_description.length > 500
            ? `${proposal.proposed_description.slice(0, 500)}...`
            : proposal.proposed_description}
        </div>

        {pipelineLabel && (
          <div className="mt-3">
            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
              <GitBranch className="h-3 w-3" aria-hidden="true" />
              Agent Pipeline: {pipelineLabel}
            </span>
          </div>
        )}
      </div>

      <div className="flex gap-2 border-t border-border bg-background/42 p-3">
        {isExpired ? (
          <span className="flex-1 text-center text-sm text-muted-foreground py-2">
            Proposal expired
          </span>
        ) : (
          <>
            <button
              type="button"
              onClick={onReject}
              className="flex-1 rounded-full border border-border bg-background/72 px-4 py-2 text-sm font-medium cursor-pointer text-muted-foreground transition-colors hover:bg-primary/10 hover:text-foreground"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onConfirm}
              className="flex-1 py-2 px-4 rounded-md text-sm font-medium cursor-pointer transition-colors bg-primary text-primary-foreground border-none hover:bg-primary/90"
            >
              Create Task
            </button>
          </>
        )}
      </div>
    </div>
  );
});
