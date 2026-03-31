/**
 * PlanPreview — Rich plan display card for the /plan planning mode.
 *
 * Shows plan title, summary, ordered steps with dependency annotations,
 * status badges, and action buttons (Request Changes, Approve, Exit).
 */

import type { PlanCreateActionData, PlanApprovalResponse } from '@/types';
import { Check, ExternalLink, GitBranch, Loader2, ListChecks, X } from '@/lib/icons';
import { cn } from '@/lib/utils';

interface PlanPreviewProps {
  plan: PlanCreateActionData;
  onApprove?: (planId: string) => Promise<PlanApprovalResponse>;
  onExit?: (planId: string) => Promise<void>;
  onRequestChanges?: () => void;
  /** Updated plan data after approval (with issue links). */
  approvedData?: PlanApprovalResponse | null;
  isApproving?: boolean;
  approveError?: string | null;
}

const STATUS_BADGES: Record<string, { label: string; className: string }> = {
  draft: { label: 'Draft', className: 'bg-yellow-500/15 text-yellow-700 dark:text-yellow-400' },
  approved: { label: 'Approved', className: 'bg-blue-500/15 text-blue-700 dark:text-blue-400' },
  completed: { label: 'Completed', className: 'bg-green-500/15 text-green-700 dark:text-green-400' },
  failed: { label: 'Failed', className: 'bg-red-500/15 text-red-700 dark:text-red-400' },
};

export function PlanPreview({
  plan,
  onApprove,
  onExit,
  onRequestChanges,
  approvedData,
  isApproving = false,
  approveError = null,
}: PlanPreviewProps) {
  const status = approvedData?.status ?? plan.status;
  const badge = STATUS_BADGES[status] || STATUS_BADGES.draft;

  // Build a map of step_id -> issue data from approvedData
  const stepIssueMap = new Map<string, { issue_number?: number; issue_url?: string }>();
  if (approvedData?.steps) {
    for (const s of approvedData.steps) {
      stepIssueMap.set(s.step_id, { issue_number: s.issue_number, issue_url: s.issue_url });
    }
  }

  return (
    <div className="ml-11 max-w-[600px] self-start overflow-hidden rounded-lg border border-border bg-background/56">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 bg-primary/5 px-4 py-2.5 border-b border-border">
        <div className="flex items-center gap-2 min-w-0">
          <ListChecks className="h-4 w-4 text-primary shrink-0" />
          <span className="text-xs font-medium text-muted-foreground truncate">
            Plan Preview
          </span>
          {plan.repo_owner && plan.repo_name && (
            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
              <GitBranch className="h-3 w-3" aria-hidden="true" />
              {plan.repo_owner}/{plan.repo_name}
            </span>
          )}
        </div>
        <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-medium', badge.className)}>
          {badge.label}
        </span>
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="text-base font-semibold text-foreground mb-2">{plan.title}</h3>
        <p className="text-sm text-muted-foreground leading-relaxed mb-4">
          {plan.summary.length > 500 ? `${plan.summary.slice(0, 500)}...` : plan.summary}
        </p>

        {/* Steps */}
        {plan.steps.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Steps ({plan.steps.length})
            </h4>
            <ol className="space-y-1.5">
              {plan.steps.map((step) => {
                const issueData = stepIssueMap.get(step.step_id);
                return (
                  <li key={step.step_id} className="flex items-start gap-2 text-sm">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-medium text-muted-foreground mt-0.5">
                      {step.position + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="font-medium text-foreground">{step.title}</span>
                        {issueData?.issue_number && (
                          <a
                            href={issueData.issue_url || '#'}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-0.5 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground hover:text-foreground transition-colors"
                          >
                            #{issueData.issue_number}
                            <ExternalLink className="h-2.5 w-2.5" />
                          </a>
                        )}
                      </div>
                      {step.dependencies.length > 0 && (
                        <span className="text-[10px] text-muted-foreground/60">
                          depends on: {step.dependencies.map((depId) => {
                            const depStep = plan.steps.find((s) => s.step_id === depId);
                            return depStep ? `Step ${depStep.position + 1}` : depId;
                          }).join(', ')}
                        </span>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>
        )}

        {/* Error */}
        {approveError && (
          <div className="mt-3 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
            {approveError}
          </div>
        )}

        {/* Completed state: parent issue link */}
        {approvedData?.parent_issue_url && (
          <div className="mt-4 pt-3 border-t border-border">
            <a
              href={approvedData.parent_issue_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:text-primary/80 transition-colors"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              View Parent Issue #{approvedData.parent_issue_number}
            </a>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-2 border-t border-border bg-background/42 p-3">
        {status === 'draft' && (
          <>
            {onRequestChanges && (
              <button
                type="button"
                onClick={onRequestChanges}
                className="flex-1 rounded-full border border-border bg-background/72 px-4 py-2 text-sm font-medium cursor-pointer text-muted-foreground transition-colors hover:bg-primary/10 hover:text-foreground"
              >
                Request Changes
              </button>
            )}
            {onApprove && (
              <button
                type="button"
                onClick={() => onApprove(plan.plan_id)}
                disabled={isApproving}
                className="flex-1 py-2 px-4 rounded-md text-sm font-medium cursor-pointer transition-colors bg-primary text-primary-foreground border-none hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isApproving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Creating Issues...
                  </>
                ) : (
                  <>
                    <Check className="h-4 w-4" />
                    Approve & Create Issues
                  </>
                )}
              </button>
            )}
          </>
        )}
        {(status === 'completed' || status === 'failed') && onExit && (
          <button
            type="button"
            onClick={() => onExit(plan.plan_id)}
            className="flex-1 rounded-full border border-border bg-background/72 px-4 py-2 text-sm font-medium cursor-pointer text-muted-foreground transition-colors hover:bg-primary/10 hover:text-foreground flex items-center justify-center gap-2"
          >
            <X className="h-4 w-4" />
            Exit Plan Mode
          </button>
        )}
      </div>
    </div>
  );
}
