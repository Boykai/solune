/**
 * InstallConfirmDialog — confirmation dialog before installing an imported agent.
 *
 * Shows agent details, target repo, and files that will be committed.
 * Prevents accidental GitHub writes by requiring explicit confirmation.
 */

import { useState } from 'react';
import { AlertCircle, Loader2 } from '@/lib/icons';
import { useInstallAgent } from '@/hooks/useAgents';
import { Button } from '@/components/ui/button';
import type { AgentConfig } from '@/services/api';

interface InstallConfirmDialogProps {
  agent: AgentConfig;
  projectId: string;
  owner?: string;
  repo?: string;
  isOpen: boolean;
  onClose: () => void;
}

export function InstallConfirmDialog({
  agent,
  projectId,
  owner,
  repo,
  isOpen,
  onClose,
}: InstallConfirmDialogProps) {
  const installMutation = useInstallAgent(projectId);
  const [error, setError] = useState<string | null>(null);

  const handleInstall = async () => {
    setError(null);
    try {
      await installMutation.mutateAsync(agent.id);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Install failed');
    }
  };

  if (!isOpen) return null;

  const targetRepo = owner && repo ? `${owner}/${repo}` : 'the connected repository';
  const agentPath = `.github/agents/${agent.slug}.agent.md`;
  const promptPath = `.github/prompts/${agent.slug}.prompt.md`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-2xl bg-[var(--color-bg-card)] shadow-2xl">
        {/* Header */}
        <div className="border-b border-[var(--color-border)] p-6">
          <h2 className="text-lg font-semibold text-[var(--color-text)]">
            Install Agent to Repository
          </h2>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            This will create a GitHub issue and pull request.
          </p>
        </div>

        {/* Body */}
        <div className="space-y-4 p-6">
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
              Agent
            </label>
            <p className="mt-1 font-medium text-[var(--color-text)]">{agent.name}</p>
            <p className="text-sm text-[var(--color-text-muted)]">{agent.description}</p>
          </div>

          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
              Target Repository
            </label>
            <p className="mt-1 font-mono text-sm text-[var(--color-text)]">{targetRepo}</p>
          </div>

          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
              Files to commit
            </label>
            <div className="mt-1 space-y-1">
              <p className="font-mono text-xs text-[var(--color-text-muted)]">{agentPath}</p>
              <p className="font-mono text-xs text-[var(--color-text-muted)]">{promptPath}</p>
            </div>
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
              <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 border-t border-[var(--color-border)] p-4">
          <Button variant="outline" onClick={onClose} disabled={installMutation.isPending}>
            Cancel
          </Button>
          <Button onClick={() => void handleInstall()} disabled={installMutation.isPending}>
            {installMutation.isPending ? (
              <>
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                Installing…
              </>
            ) : (
              'Install'
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
