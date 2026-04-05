/**
 * InstallConfirmDialog — confirmation dialog before installing an imported agent.
 *
 * Shows agent details, target repo, and files that will be committed.
 * Prevents accidental GitHub writes by requiring explicit confirmation.
 */

import { useCallback, useState } from 'react';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
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

  const handleClose = useCallback(() => {
    setError(null);
    onClose();
  }, [onClose]);

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

  return (
    <AlertDialog open={isOpen} onOpenChange={(open) => { if (!open && !installMutation.isPending) handleClose(); }}>
      <AlertDialogContent
        overlayClassName="z-[var(--z-install-confirm)]"
        className="z-[var(--z-install-confirm)] max-w-lg overflow-hidden rounded-[1.5rem] border-border/80 bg-card p-0"
      >
        <AlertDialogHeader className="border-b border-border/70 bg-background/72 px-6 py-5">
          <AlertDialogTitle>Install Agent to Repository</AlertDialogTitle>
          <AlertDialogDescription>
            This will create a GitHub issue and pull request.
          </AlertDialogDescription>
        </AlertDialogHeader>

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

        <AlertDialogFooter className="border-t border-border/70 bg-background/72 px-6 py-4">
          <AlertDialogCancel asChild>
            <Button variant="outline" disabled={installMutation.isPending}>
              Cancel
            </Button>
          </AlertDialogCancel>
          <AlertDialogAction asChild onClick={(event) => event.preventDefault()}>
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
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
