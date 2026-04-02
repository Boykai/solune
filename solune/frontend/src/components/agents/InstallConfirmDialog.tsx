/**
 * InstallConfirmDialog — confirmation dialog before installing an imported agent.
 *
 * Shows agent details, target repo, and files that will be committed.
 * Prevents accidental GitHub writes by requiring explicit confirmation.
 */

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { AlertCircle, Loader2 } from '@/lib/icons';
import { useInstallAgent } from '@/hooks/useAgents';
import { useScrollLock } from '@/hooks/useScrollLock';
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

  useScrollLock(isOpen);

  const handleClose = () => {
    setError(null);
    onClose();
  };

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        handleClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const handleInstall = async () => {
    setError(null);
    try {
      await installMutation.mutateAsync(agent.id);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Install failed');
    }
  };

  if (!isOpen) return null;

  const targetRepo = owner && repo ? `${owner}/${repo}` : 'the connected repository';
  const agentPath = `.github/agents/${agent.slug}.agent.md`;
  const promptPath = `.github/prompts/${agent.slug}.prompt.md`;

  const handleBackdropClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) {
      handleClose();
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[var(--z-install-confirm)] flex items-center justify-center bg-background/80 px-4 backdrop-blur-sm"
      role="presentation"
      onClick={handleBackdropClick}
    >
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions */}
      <div
        className="celestial-panel celestial-fade-in w-full max-w-lg overflow-hidden rounded-[1.5rem] border border-border/80 bg-card shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="install-confirm-title"
        onClick={(event) => event.stopPropagation()}
      >
        {/* Header */}
        <div className="border-b border-border/70 bg-background/72 px-6 py-5">
          <h2 id="install-confirm-title" className="text-lg font-semibold text-foreground">
            Install Agent to Repository
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            This will create a GitHub issue and pull request.
          </p>
        </div>

        {/* Body */}
        <div className="space-y-4 bg-background/50 px-6 py-5">
          <div className="rounded-[1.2rem] border border-border/70 bg-background/78 p-4">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Agent
            </span>
            <p className="mt-1 font-medium text-foreground">{agent.name}</p>
            <p className="text-sm text-muted-foreground">{agent.description}</p>
          </div>

          <div className="rounded-[1.2rem] border border-border/70 bg-background/78 p-4">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Target Repository
            </span>
            <p className="mt-1 font-mono text-sm text-foreground">{targetRepo}</p>
          </div>

          <div className="rounded-[1.2rem] border border-border/70 bg-background/78 p-4">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Files to commit
            </span>
            <div className="mt-1 space-y-1">
              <p className="font-mono text-xs text-muted-foreground">{agentPath}</p>
              <p className="font-mono text-xs text-muted-foreground">{promptPath}</p>
            </div>
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-[1rem] border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 border-t border-border/70 bg-background/72 px-6 py-4">
          <Button variant="outline" onClick={handleClose} disabled={installMutation.isPending}>
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
    </div>,
    document.body
  );
}
