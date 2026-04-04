/**
 * MCP Configuration settings component.
 *
 * Provides add/view/remove MCP configurations with inline validation,
 * confirmation dialogs, loading states, and auth error handling.
 * Integrates as a SettingsSection in the Settings page.
 */

import { useState, useCallback, useMemo, useRef } from 'react';
import { SettingsSection } from './SettingsSection';
import { useMcpSettings } from '@/hooks/useMcpSettings';
import { authApi, ApiError } from '@/services/api';
import { TOAST_SUCCESS_MS } from '@/constants';
import type { McpConfiguration } from '@/types';
import { cn } from '@/lib/utils';
import { CharacterCounter } from '@/components/ui/character-counter';
import { useFirstErrorFocus } from '@/hooks/useFirstErrorFocus';

// ── Validation Helpers ──

function isValidUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

// ── Sub-components ──

function ActiveStatusBadge({ isActive }: { isActive: boolean }) {
  return isActive ? (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-600 dark:text-green-400">
      <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
      Active
    </span>
  ) : (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-background/62 px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
      <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40" />
      Inactive
    </span>
  );
}

function McpListItem({
  mcp,
  onRemove,
  isDeleting,
}: {
  mcp: McpConfiguration;
  onRemove: (id: string) => void;
  isDeleting: boolean;
}) {
  const [showConfirm, setShowConfirm] = useState(false);

  return (
    <div className="flex items-center justify-between gap-4 rounded-[1rem] border border-border bg-background/46 p-4">
      <div className="flex flex-col gap-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground truncate">{mcp.name}</span>
          <ActiveStatusBadge isActive={mcp.is_active} />
        </div>
        <span className="text-xs text-muted-foreground truncate">{mcp.endpoint_url}</span>
      </div>

      {!showConfirm ? (
        <button
          className="shrink-0 inline-flex items-center justify-center px-3 py-1.5 text-sm font-medium rounded-md
            border border-destructive/30 text-destructive
            hover:bg-destructive/10 transition-colors"
          onClick={() => setShowConfirm(true)}
          type="button"
        >
          Remove
        </button>
      ) : (
        <div className="shrink-0 flex items-center gap-2">
          <button
            className="inline-flex items-center justify-center px-3 py-1.5 text-sm font-medium rounded-md
              bg-destructive text-destructive-foreground shadow-sm
              hover:bg-destructive/90 transition-colors
              disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={() => {
              onRemove(mcp.id);
              setShowConfirm(false);
            }}
            disabled={isDeleting}
            type="button"
          >
            {isDeleting ? 'Removing…' : 'Confirm'}
          </button>
          <button
            className="inline-flex items-center justify-center px-3 py-1.5 text-sm font-medium rounded-md
              border border-border text-muted-foreground
              hover:bg-primary/10 hover:text-foreground transition-colors"
            onClick={() => setShowConfirm(false)}
            type="button"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

function AddMcpForm({
  onAdd,
  isCreating,
  serverError,
  onClearError,
}: {
  onAdd: (name: string, url: string) => Promise<boolean>;
  isCreating: boolean;
  serverError: Error | null;
  onClearError: () => void;
}) {
  const nameRef = useRef<HTMLInputElement>(null);
  const urlRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState('');
  const [endpointUrl, setEndpointUrl] = useState('');
  const [nameError, setNameError] = useState('');
  const [urlError, setUrlError] = useState('');

  const fieldRefs = useMemo(() => ({ name: nameRef, url: urlRef }), []);
  const errors = useMemo(() => ({ name: nameError || null, url: urlError || null }), [nameError, urlError]);
  const focusFirstError = useFirstErrorFocus(fieldRefs, errors);

  const validateName = (value: string): string => {
    if (!value.trim()) return 'Name is required';
    if (value.length > 100) return 'Name must be 100 characters or less';
    return '';
  };

  const validateUrl = (value: string): string => {
    if (!value.trim()) return 'Endpoint URL is required';
    if (value.length > 2048) return 'URL must be 2048 characters or less';
    if (!isValidUrl(value)) return 'Please enter a valid HTTP or HTTPS URL';
    return '';
  };

  const validate = (): boolean => {
    const newNameError = validateName(name);
    const newUrlError = validateUrl(endpointUrl);
    setNameError(newNameError);
    setUrlError(newUrlError);
    if (newNameError || newUrlError) {
      requestAnimationFrame(() => focusFirstError());
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    onClearError();
    if (validate()) {
      const success = await onAdd(name.trim(), endpointUrl.trim());
      if (success) {
        setName('');
        setEndpointUrl('');
      }
    }
  };

  const getServerErrorMessage = (): string | null => {
    if (!serverError) return null;

    if (serverError instanceof ApiError) {
      // Prefer standard AppException shape: { error: string }
      const detailFromErrorField = serverError.error?.error;
      if (detailFromErrorField) return detailFromErrorField;

      // Also support FastAPI HTTPException shape: { detail: string }
      const detailFromDetailField = serverError.error?.details?.detail;
      if (typeof detailFromDetailField === 'string' && detailFromDetailField.trim()) {
        return detailFromDetailField;
      }

      // Fallback to the error message, but avoid showing literal "undefined"
      if (serverError.message && serverError.message !== 'undefined') {
        return serverError.message;
      }

      return 'An unexpected error occurred';
    }

    // Non-ApiError: use message if it looks meaningful
    if (serverError.message && serverError.message !== 'undefined') {
      return serverError.message;
    }

    return 'An unexpected error occurred';
  };

  const serverErrorMsg = getServerErrorMessage();

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <h4 className="text-sm font-medium text-foreground">Add New MCP</h4>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="mcp-name" className="text-sm text-muted-foreground">
          Name
        </label>
        <input
          id="mcp-name"
          ref={nameRef}
          type="text"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            if (nameError) setNameError('');
          }}
          onBlur={() => setNameError(validateName(name))}
          placeholder="My MCP Server"
          maxLength={100}
          aria-invalid={!!nameError}
          aria-describedby={nameError ? 'mcp-name-error' : undefined}
          className={cn('celestial-focus px-3 py-2 text-sm rounded-md border bg-background/72 text-foreground placeholder:text-muted-foreground/50 focus:outline-none', nameError ? 'border-destructive' : 'border-border')}
          disabled={isCreating}
        />
        <div className="mt-0.5 flex items-center justify-between">
          {nameError ? <p id="mcp-name-error" className="text-xs text-destructive">{nameError}</p> : <span />}
          <CharacterCounter current={name.length} max={100} />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="mcp-endpoint" className="text-sm text-muted-foreground">
          Endpoint URL
        </label>
        <input
          id="mcp-endpoint"
          ref={urlRef}
          type="text"
          value={endpointUrl}
          onChange={(e) => {
            setEndpointUrl(e.target.value);
            if (urlError) setUrlError('');
          }}
          onBlur={() => setUrlError(validateUrl(endpointUrl))}
          placeholder="https://example.com/mcp"
          maxLength={2048}
          aria-invalid={!!urlError}
          aria-describedby={urlError ? 'mcp-endpoint-error' : undefined}
          className={cn('celestial-focus px-3 py-2 text-sm rounded-md border bg-background/72 text-foreground placeholder:text-muted-foreground/50 focus:outline-none', urlError ? 'border-destructive' : 'border-border')}
          disabled={isCreating}
        />
        <div className="mt-0.5 flex items-center justify-between">
          {urlError ? <p id="mcp-endpoint-error" className="text-xs text-destructive">{urlError}</p> : <span />}
          <CharacterCounter current={endpointUrl.length} max={2048} />
        </div>
      </div>

      {serverErrorMsg && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3">
          <p className="text-sm text-destructive">{serverErrorMsg}</p>
        </div>
      )}

      <button
        type="submit"
        className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-md
          bg-primary text-primary-foreground shadow-sm
          hover:bg-primary/90 transition-colors
          disabled:opacity-50 disabled:cursor-not-allowed
          w-fit"
        disabled={isCreating}
      >
        {isCreating ? (
          <>
            <span className="w-3.5 h-3.5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
            Adding…
          </>
        ) : (
          'Add MCP'
        )}
      </button>
    </form>
  );
}

// ── Main Component ──

export function McpSettings() {
  const {
    mcps,
    isLoading,
    error,
    createMcp,
    isCreating,
    createError,
    resetCreateError,
    deleteMcp,
    deletingId,
    deleteError,
    resetDeleteError,
    authError,
  } = useMcpSettings();

  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const showSuccess = useCallback((msg: string) => {
    setSuccessMessage(msg);
    setTimeout(() => setSuccessMessage(null), TOAST_SUCCESS_MS);
  }, []);

  const handleAdd = useCallback(
    async (name: string, url: string): Promise<boolean> => {
      try {
        await createMcp({ name, endpoint_url: url });
        showSuccess(`MCP "${name}" added successfully`);
        return true;
      } catch {
        // Error is captured by the mutation state
        return false;
      }
    },
    [createMcp, showSuccess]
  );

  const handleRemove = useCallback(
    async (mcpId: string) => {
      try {
        resetDeleteError();
        await deleteMcp(mcpId);
        showSuccess('MCP removed successfully');
      } catch {
        // Error is captured by the mutation state
      }
    },
    [deleteMcp, showSuccess, resetDeleteError]
  );

  // Extract a human-readable message from a delete error
  const getDeleteErrorMessage = (): string => {
    if (!deleteError) return 'Failed to delete MCP configuration.';
    if (deleteError instanceof ApiError) {
      return (
        deleteError.error?.error ||
        (typeof deleteError.error?.details?.detail === 'string'
          ? deleteError.error.details.detail
          : null) ||
        (deleteError.message !== 'undefined' ? deleteError.message : null) ||
        'Failed to delete MCP configuration.'
      );
    }
    return deleteError.message && deleteError.message !== 'undefined'
      ? deleteError.message
      : 'Failed to delete MCP configuration.';
  };

  const handleLogin = useCallback(() => {
    authApi.login();
  }, []);

  // Auth error state — prompt re-authentication
  if (authError) {
    return (
      <SettingsSection
        title="MCP Configurations"
        description="Manage Model Context Protocol servers for your GitHub agents."
        hideSave
      >
        <div className="flex flex-col gap-3 rounded-[1rem] border border-primary/20 bg-primary/10 p-4">
          <p className="text-sm text-yellow-700 dark:text-yellow-300">
            Your session has expired. Please sign in again.
          </p>
          <button
            className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-full
              bg-primary text-primary-foreground shadow-sm
              hover:bg-primary/90 transition-colors w-fit"
            onClick={handleLogin}
            type="button"
          >
            Sign In
          </button>
        </div>
      </SettingsSection>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <SettingsSection
        title="MCP Configurations"
        description="Manage Model Context Protocol servers for your GitHub agents."
        hideSave
      >
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <div className="w-4 h-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
          Loading MCP configurations…
        </div>
      </SettingsSection>
    );
  }

  // Load error (non-auth) — authError is already handled above so the
  // redundant `!authError` guard has been removed for clarity.
  if (error) {
    return (
      <SettingsSection
        title="MCP Configurations"
        description="Manage Model Context Protocol servers for your GitHub agents."
        hideSave
      >
        <div className="flex flex-col gap-3 rounded-md border border-destructive/30 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">
            Failed to load MCP configurations. Please try again.
          </p>
        </div>
      </SettingsSection>
    );
  }

  return (
    <SettingsSection
      title="MCP Configurations"
      description="Manage Model Context Protocol servers for your GitHub agents."
      hideSave
    >
      {/* Success Message */}
      {successMessage && (
        <div className="rounded-[1rem] border border-green-500/30 bg-green-500/10 p-3">
          <p className="text-sm text-green-700 dark:text-green-400">{successMessage}</p>
        </div>
      )}

      {/* Delete Error */}
      {deleteError && (
        <div className="rounded-[1rem] border border-destructive/30 bg-destructive/10 p-3">
          <p className="text-sm text-destructive">{getDeleteErrorMessage()}</p>
        </div>
      )}

      {/* MCP List */}
      {mcps.length === 0 ? (
        <div className="rounded-[1rem] border border-border bg-background/40 p-6 text-center">
          <p className="text-sm text-muted-foreground">
            No MCPs configured yet. Add one to get started.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {mcps.map((mcp) => (
            <McpListItem
              key={mcp.id}
              mcp={mcp}
              onRemove={handleRemove}
              isDeleting={deletingId === mcp.id}
            />
          ))}
        </div>
      )}

      {/* Add MCP Form */}
      <div className="border-t border-border pt-5">
        <AddMcpForm
          onAdd={handleAdd}
          isCreating={isCreating}
          serverError={createError}
          onClearError={resetCreateError}
        />
      </div>
    </SettingsSection>
  );
}
