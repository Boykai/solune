/**
 * ConfirmationDialog — reusable, accessible confirmation dialog for critical actions.
 *
 * Built on @radix-ui/react-alert-dialog for automatic focus trapping,
 * scroll lock, and accessible Escape handling.
 *
 * Supports danger/warning/info variants, async loading states with spinner,
 * inline error display, and ARIA attributes for WCAG 2.1 AA.
 */

import { AlertTriangle, Info, Loader2 } from '@/lib/icons';
import * as AlertDialogPrimitive from '@radix-ui/react-alert-dialog';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export type ConfirmationVariant = 'danger' | 'warning' | 'info';

export interface ConfirmationDialogProps {
  isOpen: boolean;
  title: string;
  description: string;
  variant: ConfirmationVariant;
  confirmLabel: string;
  cancelLabel: string;
  isLoading: boolean;
  error: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

const VARIANT_CONFIG: Record<
  ConfirmationVariant,
  {
    Icon: typeof AlertTriangle | typeof Info;
    iconClass: string;
    iconBgClass: string;
    confirmBtnClass: string;
  }
> = {
  danger: {
    Icon: AlertTriangle,
    iconClass: 'text-red-500',
    iconBgClass: 'bg-red-100/80 dark:bg-red-950/50',
    confirmBtnClass:
      'bg-red-600 hover:bg-red-700 text-white disabled:opacity-50 disabled:cursor-not-allowed',
  },
  warning: {
    Icon: AlertTriangle,
    iconClass: 'text-amber-500',
    iconBgClass: 'bg-amber-100/80 dark:bg-amber-950/50',
    confirmBtnClass:
      'bg-amber-600 hover:bg-amber-700 text-white disabled:opacity-50 disabled:cursor-not-allowed',
  },
  info: {
    Icon: Info,
    iconClass: 'text-blue-500',
    iconBgClass: 'bg-blue-100/80 dark:bg-blue-950/50',
    confirmBtnClass:
      'bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50 disabled:cursor-not-allowed',
  },
};

export function ConfirmationDialog({
  isOpen,
  title,
  description,
  variant,
  confirmLabel,
  cancelLabel,
  isLoading,
  error,
  onConfirm,
  onCancel,
}: ConfirmationDialogProps) {
  const { Icon, iconClass, iconBgClass, confirmBtnClass } = VARIANT_CONFIG[variant];

  return (
    <AlertDialogPrimitive.Root
      open={isOpen}
      onOpenChange={(open) => {
        if (!open && !isLoading) onCancel();
      }}
    >
      <AlertDialogPrimitive.Portal>
        <AlertDialogPrimitive.Overlay className="fixed inset-0 z-[var(--z-modal-backdrop,60)] bg-black/50 motion-safe:data-[state=open]:animate-in motion-safe:data-[state=open]:fade-in-0 motion-safe:data-[state=closed]:animate-out motion-safe:data-[state=closed]:fade-out-0" />

        <AlertDialogPrimitive.Content
          className="fixed left-1/2 top-1/2 z-[var(--z-modal,70)] mx-4 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border/80 bg-card p-6 shadow-xl motion-safe:animate-in motion-safe:fade-in-0 motion-safe:zoom-in-95 motion-safe:data-[state=closed]:animate-out motion-safe:data-[state=closed]:fade-out-0 motion-safe:data-[state=closed]:zoom-out-95"
          onEscapeKeyDown={(e) => {
            if (isLoading) e.preventDefault();
          }}
        >
          {/* Header */}
          <div className="flex items-start gap-3">
            <div className={cn('shrink-0 rounded-full p-2', iconBgClass)}>
              <Icon className={cn('h-5 w-5', iconClass)} />
            </div>
            <AlertDialogPrimitive.Title className="text-base font-semibold text-foreground pt-1.5">
              {title}
            </AlertDialogPrimitive.Title>
          </div>

          {/* Description (scrollable) */}
          <AlertDialogPrimitive.Description className="mt-3 max-h-[60vh] overflow-y-auto text-sm leading-relaxed text-muted-foreground">
            {description}
          </AlertDialogPrimitive.Description>

          {/* Error */}
          {error && (
            <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-400">
              {error}
            </div>
          )}

          {/* Buttons */}
          <div className="mt-5 flex justify-end gap-2">
            <AlertDialogPrimitive.Cancel asChild>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="rounded-lg text-foreground"
                disabled={isLoading}
              >
                {cancelLabel}
              </Button>
            </AlertDialogPrimitive.Cancel>
            <AlertDialogPrimitive.Action asChild onClick={(e) => e.preventDefault()}>
              <Button
                type="button"
                size="sm"
                className={cn('gap-2 rounded-lg', confirmBtnClass)}
                onClick={onConfirm}
                disabled={isLoading}
              >
                {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                {isLoading ? 'Processing…' : confirmLabel}
              </Button>
            </AlertDialogPrimitive.Action>
          </div>
        </AlertDialogPrimitive.Content>
      </AlertDialogPrimitive.Portal>
    </AlertDialogPrimitive.Root>
  );
}
