/**
 * ConfirmChoreModal — two-step confirmation modal for new Chore creation.
 *
 * Step 1: Informs the user the Chore will be saved.
 * Step 2: Final confirmation to create the Chore.
 */

import { useState } from 'react';
import { AlertTriangle, CheckCircle, Loader2 } from '@/lib/icons';
import { Button } from '@/components/ui/button';

interface ConfirmChoreModalProps {
  isOpen: boolean;
  choreName: string;
  isLoading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmChoreModal({
  isOpen,
  choreName,
  isLoading,
  onConfirm,
  onCancel,
}: ConfirmChoreModalProps) {
  if (!isOpen) return null;

  return (
    <ConfirmChoreModalContent
      choreName={choreName}
      isLoading={isLoading}
      onConfirm={onConfirm}
      onCancel={onCancel}
    />
  );
}

interface ConfirmChoreModalContentProps {
  choreName: string;
  isLoading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

function ConfirmChoreModalContent({
  choreName,
  isLoading,
  onConfirm,
  onCancel,
}: ConfirmChoreModalContentProps) {
  const [step, setStep] = useState<1 | 2>(1);

  return (
    <div className="fixed inset-0 z-[var(--z-modal-backdrop)] flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50"
        onClick={isLoading ? undefined : onCancel}
        role="presentation"
      />
      <div className="celestial-panel celestial-fade-in relative z-10 w-full max-w-md mx-4 rounded-lg border border-border bg-background shadow-xl">
        {step === 1 ? (
          <div className="p-6 flex flex-col items-center gap-4 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-yellow-100 dark:bg-yellow-900/30">
              <AlertTriangle className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">Create New Chore</h3>
            <p className="text-sm text-muted-foreground">
              Creating <strong>&ldquo;{choreName}&rdquo;</strong> will save the chore definition
              and enable scheduling for this project.
            </p>
            <div className="flex gap-3 pt-2">
              <Button variant="outline" onClick={onCancel}>
                Cancel
              </Button>
              <Button onClick={() => setStep(2)}>I Understand, Continue</Button>
            </div>
          </div>
        ) : (
          <div className="p-6 flex flex-col items-center gap-4 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
              <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">Confirm Chore Creation</h3>
            <p className="text-sm text-muted-foreground">
              This will create a GitHub Issue and save the chore definition to the database.
              You can schedule, trigger, or pause it at any time.
            </p>
            <div className="flex gap-3 pt-2">
              <Button variant="outline" onClick={() => setStep(1)} disabled={isLoading}>
                Back
              </Button>
              <Button onClick={onConfirm} disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating…
                  </>
                ) : (
                  'Yes, Create Chore'
                )}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
