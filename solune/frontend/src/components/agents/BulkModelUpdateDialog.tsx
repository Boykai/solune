/**
 * BulkModelUpdateDialog — two-step confirmation dialog for updating
 * all agent models at once.
 *
 * Step 1: Select a target model.
 * Step 2: Review affected agents and confirm.
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useBulkUpdateModels } from '@/hooks/useAgents';
import { ModelSelector } from '@/components/pipeline/ModelSelector';
import type { AgentConfig } from '@/services/api';

interface BulkModelUpdateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agents: AgentConfig[];
  projectId: string;
  onSuccess: () => void;
}

export function BulkModelUpdateDialog({
  open,
  onOpenChange,
  agents,
  projectId,
  onSuccess,
}: BulkModelUpdateDialogProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [selectedModelName, setSelectedModelName] = useState<string>('');

  const mutation = useBulkUpdateModels(projectId);

  const handleClose = () => {
    setStep(1);
    setSelectedModelId(null);
    setSelectedModelName('');
    onOpenChange(false);
  };

  const handleConfirm = () => {
    if (!selectedModelId || !selectedModelName) return;
    mutation.mutate(
      { targetModelId: selectedModelId, targetModelName: selectedModelName },
      {
        onSuccess: () => {
          handleClose();
          onSuccess();
        },
      }
    );
  };

  if (!open) return null;

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => { if (!nextOpen && !mutation.isPending) handleClose(); }}>
      <DialogContent hideClose className="max-h-[80vh] max-w-md overflow-y-auto">
        {step === 1 && (
          <>
            <DialogHeader className="mb-4">
              <DialogTitle>Update All Agent Models</DialogTitle>
              <DialogDescription>
                Select the target model to apply to all {agents.length} agent
                {agents.length === 1 ? '' : 's'}.
              </DialogDescription>
            </DialogHeader>
            <div className="mb-4">
              <ModelSelector
                selectedModelId={selectedModelId}
                onSelect={(id, name) => {
                  setSelectedModelId(id);
                  setSelectedModelName(name);
                }}
              />
            </div>
            {selectedModelName && (
              <p className="mb-4 text-sm">
                Selected: <span className="font-medium">{selectedModelName}</span>
              </p>
            )}
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={handleClose}
                disabled={mutation.isPending}
              >
                Cancel
              </Button>
              <Button
                type="button"
                disabled={!selectedModelId}
                onClick={() => setStep(2)}
              >
                Next
              </Button>
            </DialogFooter>
          </>
        )}

        {step === 2 && (
          <>
            <DialogHeader className="mb-3">
              <DialogTitle>Confirm Bulk Update</DialogTitle>
              <DialogDescription>
                Update all agents to <span className="font-medium">{selectedModelName}</span>?
              </DialogDescription>
            </DialogHeader>
            <div className="mb-4 rounded-md border border-border/60 bg-background/50 p-3 max-h-48 overflow-y-auto">
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {agents.length} agent{agents.length === 1 ? '' : 's'} will be updated
              </p>
              <ul className="space-y-1">
                {agents.map((agent) => (
                  <li key={agent.id} className="flex items-center justify-between text-sm">
                    <span className="truncate">{agent.name}</span>
                    <span className="shrink-0 ml-2 text-xs text-muted-foreground">
                      {agent.default_model_name || 'No model'} → {selectedModelName}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            {mutation.isError && (
              <div className="mb-3 text-sm text-destructive bg-destructive/10 rounded-md p-2">
                {mutation.error?.message || 'Bulk update failed'}
              </div>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setStep(1)}
              >
                Back
              </Button>
              <Button
                type="button"
                disabled={mutation.isPending}
                onClick={handleConfirm}
              >
                {mutation.isPending ? 'Updating…' : 'Confirm'}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
