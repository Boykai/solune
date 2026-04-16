/**
 * PipelineToolbar — persistent action bar with Create/Save/Delete/Discard.
 * Save is always enabled during creation/editing. Presets show "Save as Copy".
 */

import { useEffect, useState } from 'react';
import { Save, Copy, Trash2, RotateCcw, Loader2 } from '@/lib/icons';
import { Button } from '@/components/ui/button';
import type { PipelineBoardState, PipelineValidationErrors } from '@/types';
import { useScrollLock } from '@/hooks/useScrollLock';

interface PipelineToolbarProps {
  boardState: PipelineBoardState;
  isDirty: boolean;
  isSaving: boolean;
  isPreset: boolean;
  pipelineName?: string;
  validationErrors: PipelineValidationErrors;
  onSave: () => void;
  onSaveAsCopy: (newName: string) => void;
  onDelete: () => void;
  onDiscard: () => void;
}

export function PipelineToolbar({
  boardState,
  isDirty,
  isSaving,
  isPreset,
  pipelineName,
  validationErrors,
  onSave,
  onSaveAsCopy,
  onDelete,
  onDiscard,
}: PipelineToolbarProps) {
  const [showCopyDialog, setShowCopyDialog] = useState(false);
  const [copyName, setCopyName] = useState('');

  const errorCount = Object.keys(validationErrors).length;
  const hasValidationErrors = errorCount > 0;
  const isEditingPreset = boardState === 'editing' && isPreset;
  const isEditingSavedPipeline = boardState === 'editing' && !isPreset;
  const validationErrorLabel =
    errorCount === 0
      ? ''
      : `${errorCount} validation error${errorCount === 1 ? '' : 's'}`;
  const isSaveEnabled =
    !hasValidationErrors &&
    (boardState === 'creating' || (boardState === 'editing' && !isPreset));
  const isSaveAsCopyEnabled = !isSaving && !hasValidationErrors;
  const isDiscardEnabled =
    (boardState === 'creating' && isDirty) || (boardState === 'editing' && isDirty);
  const isDeleteEnabled = boardState === 'editing' && !isPreset;
  const copyActionLabel = isEditingPreset ? 'Save as Copy' : 'Copy';
  const copyDialogTitle = isEditingPreset ? 'Save as Copy' : 'Copy pipeline';
  const copyDialogConfirmLabel = isEditingPreset ? 'Save' : 'Copy';
  const copyActionAriaLabel =
    errorCount > 0 ? `${copyActionLabel}, ${validationErrorLabel}` : copyActionLabel;

  const closeCopyDialog = () => {
    setShowCopyDialog(false);
    setCopyName('');
  };

  const openCopyDialog = () => {
    const sourceName = pipelineName?.trim() || 'Untitled Pipeline';
    setCopyName(`${sourceName} (Copy)`);
    setShowCopyDialog(true);
  };

  const handleSaveAsCopy = () => {
    const name = copyName.trim();
    if (name) {
      onSaveAsCopy(name);
      closeCopyDialog();
    }
  };

  useScrollLock(showCopyDialog);

  useEffect(() => {
    if (!showCopyDialog) return undefined;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        closeCopyDialog();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => {
      window.removeEventListener('keydown', handleEscape);
    };
  }, [showCopyDialog]);

  return (
    <div className="pipeline-builder-toolbar moonwell flex items-center gap-2 rounded-[1rem] border border-border/65 bg-background/35 p-1.5 dark:border-border/80 dark:bg-[linear-gradient(180deg,hsl(var(--night)/0.94)_0%,hsl(var(--panel)/0.86)_100%)]">
      <div className="flex items-center gap-2">
        {isEditingPreset ? (
          <>
            <Button
              variant="default"
              size="sm"
              aria-label={copyActionAriaLabel}
              onClick={openCopyDialog}
              disabled={!isSaveAsCopyEnabled}
            >
              <Copy className="mr-1.5 h-3.5 w-3.5" />
              Save as Copy
              {errorCount > 0 && (
                <span
                  className="ml-1.5 inline-flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white"
                  aria-hidden="true"
                >
                  {errorCount}
                </span>
              )}
            </Button>

          </>
        ) : (
          <>
            <Button
              variant="default"
              size="sm"
              aria-label={errorCount > 0 ? `Save, ${validationErrorLabel}` : 'Save'}
              onClick={onSave}
              disabled={!isSaveEnabled || isSaving}
            >
              {isSaving ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="mr-1.5 h-3.5 w-3.5" />
              )}
              Save
              {errorCount > 0 && (
                <span
                  className="ml-1.5 inline-flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white"
                  aria-hidden="true"
                >
                  {errorCount}
                </span>
              )}
            </Button>

            {isEditingSavedPipeline && (
              <Button
                variant="outline"
                size="sm"
                aria-label={copyActionAriaLabel}
                onClick={openCopyDialog}
                disabled={!isSaveAsCopyEnabled}
              >
                <Copy className="mr-1.5 h-3.5 w-3.5" />
                Copy
              </Button>
            )}
          </>
        )}

        <Button variant="ghost" size="sm" onClick={onDiscard} disabled={!isDiscardEnabled}>
          <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
          Discard
        </Button>

        <Button variant="destructive" size="sm" onClick={onDelete} disabled={!isDeleteEnabled}>
          <Trash2 className="mr-1.5 h-3.5 w-3.5" />
          Delete
        </Button>
      </div>

      {showCopyDialog && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              closeCopyDialog();
            }
          }}
        >
          <div
            className="pipeline-builder-popover celestial-fade-in w-80 rounded-lg border border-border bg-card p-4 shadow-lg dark:border-border/80 dark:bg-[linear-gradient(180deg,hsl(var(--night)/0.97)_0%,hsl(var(--panel)/0.92)_100%)]"
            role="dialog"
            aria-modal="true"
            aria-labelledby="copy-dialog-title"
          >
            <h3 id="copy-dialog-title" className="mb-2 text-sm font-semibold">
              {copyDialogTitle}
            </h3>
            <input
              type="text"
              value={copyName}
              onChange={(e) => setCopyName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveAsCopy();
              }}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm dark:border-border/80 dark:bg-background/80"
              placeholder="New pipeline name"
              maxLength={100}
            />
            <div className="mt-3 flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={closeCopyDialog}>
                Cancel
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={handleSaveAsCopy}
                disabled={!copyName.trim() || hasValidationErrors}
              >
                {copyDialogConfirmLabel}
              </Button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
