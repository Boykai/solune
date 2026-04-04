import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { RepoMcpServerConfig, RepoMcpServerUpdate } from '@/types';
import { validateMcpJson } from './UploadMcpModal';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { CharacterCounter } from '@/components/ui/character-counter';
import { useFirstErrorFocus } from '@/hooks/useFirstErrorFocus';

const MAX_NAME_LENGTH = 100;

interface EditRepoMcpModalProps {
  isOpen: boolean;
  server: RepoMcpServerConfig | null;
  isSubmitting: boolean;
  submitError: string | null;
  onClose: () => void;
  onSave: (serverName: string, data: RepoMcpServerUpdate) => Promise<unknown>;
}

function buildConfigContent(server: RepoMcpServerConfig) {
  return `${JSON.stringify(
    {
      mcpServers: {
        [server.name]: server.config,
      },
    },
    null,
    2
  )}\n`;
}

export function EditRepoMcpModal({
  isOpen,
  server,
  isSubmitting,
  submitError,
  onClose,
  onSave,
}: EditRepoMcpModalProps) {
  const nameInputRef = useRef<HTMLInputElement>(null);
  const configRef = useRef<HTMLTextAreaElement>(null);
  const [name, setName] = useState('');
  const [configContent, setConfigContent] = useState('');
  const [nameError, setNameError] = useState<string | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);

  const fieldRefs = useMemo(() => ({ name: nameInputRef, config: configRef }), []);
  const errors = useMemo(() => ({ name: nameError, config: configError }), [nameError, configError]);
  const focusFirstError = useFirstErrorFocus(fieldRefs, errors);

  const handleClose = useCallback(() => {
    setNameError(null);
    setConfigError(null);
    onClose();
  }, [onClose]);

  const [prevIsOpen, setPrevIsOpen] = useState(isOpen);
  const [prevServerId, setPrevServerId] = useState(server?.name);
  if (isOpen && (isOpen !== prevIsOpen || server?.name !== prevServerId)) {
    setPrevIsOpen(true);
    setPrevServerId(server?.name);
    if (server) {
      setName(server.name);
      setConfigContent(buildConfigContent(server));
      setNameError(null);
      setConfigError(null);
    }
  } else if (!isOpen && prevIsOpen) {
    setPrevIsOpen(false);
    setPrevServerId(undefined);
  } else if (server?.name !== prevServerId) {
    setPrevServerId(server?.name);
  }

  // Focus name input when modal opens
  useEffect(() => {
    if (isOpen && server) {
      nameInputRef.current?.focus();
    }
  }, [isOpen, server]);

  if (!isOpen || !server) {
    return null;
  }

  const validateName = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) return 'Name is required';
    if (trimmed.length > MAX_NAME_LENGTH) return `Name must be ${MAX_NAME_LENGTH} characters or fewer`;
    return null;
  };

  const validateConfig = (value: string) => {
    const jsonError = validateMcpJson(value);
    if (jsonError) return jsonError;
    try {
      const parsed = JSON.parse(value) as { mcpServers?: Record<string, unknown> };
      const serverEntries = Object.keys(parsed.mcpServers ?? {});
      if (serverEntries.length !== 1) return 'Repository MCP editing supports exactly one MCP server entry';
    } catch {
      return 'Invalid JSON syntax';
    }
    return null;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    const newNameError = validateName(name);
    const newConfigError = validateConfig(configContent);
    setNameError(newNameError);
    setConfigError(newConfigError);

    if (newNameError || newConfigError) {
      // Schedule focus after state update
      requestAnimationFrame(() => focusFirstError());
      return;
    }

    try {
      await onSave(server.name, {
        name: name.trim(),
        config_content: configContent,
      });
      handleClose();
    } catch {
      // submitError is surfaced by the parent mutation state
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) handleClose(); }}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto" hideClose>
        <DialogHeader>
          <DialogTitle>Edit Repository MCP</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="rounded-xl border border-primary/20 bg-primary/5 p-3 text-sm text-muted-foreground">
            Update this MCP directly in the repository config files already present in the repo.
          </div>

          <div>
            <label htmlFor="repo-mcp-name" className="mb-1 block text-sm font-medium">
              Name
            </label>
            <input
              id="repo-mcp-name"
              ref={nameInputRef}
              type="text"
              value={name}
              onChange={(event) => {
                setName(event.target.value);
                if (nameError) setNameError(null);
              }}
              onBlur={() => setNameError(validateName(name))}
              aria-invalid={!!nameError}
              aria-describedby={nameError ? 'repo-mcp-name-error' : undefined}
              className="w-full rounded-md border border-border bg-background/72 px-3 py-2 text-sm"
              maxLength={MAX_NAME_LENGTH}
            />
            <div className="mt-1 flex items-center justify-between">
              {nameError ? (
                <p id="repo-mcp-name-error" className="text-xs text-destructive">{nameError}</p>
              ) : <span />}
              <CharacterCounter current={name.length} max={MAX_NAME_LENGTH} />
            </div>
          </div>

          <div>
            <label htmlFor="repo-mcp-config" className="mb-1 block text-sm font-medium">
              MCP Configuration
            </label>
            <textarea
              id="repo-mcp-config"
              ref={configRef}
              value={configContent}
              onChange={(event) => {
                setConfigContent(event.target.value);
                if (configError) setConfigError(null);
              }}
              onBlur={() => setConfigError(validateConfig(configContent))}
              aria-invalid={!!configError}
              aria-describedby={configError ? 'repo-mcp-config-error' : undefined}
              className="w-full rounded-md border border-border bg-background/72 px-3 py-2 text-xs font-mono leading-relaxed min-h-[180px] resize-y"
            />
            {configError && (
              <p id="repo-mcp-config-error" className="mt-1 text-xs text-destructive">{configError}</p>
            )}
          </div>

          {submitError && (
            <div className="rounded-md bg-destructive/10 p-2 text-sm text-destructive">
              {submitError}
            </div>
          )}

          {isSubmitting && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <div className="h-3 w-3 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              Saving repository MCP...
            </div>
          )}

          <DialogFooter>
            <button
              type="button"
              className="rounded-full border border-border bg-background/72 px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-primary/10 hover:text-foreground"
              onClick={handleClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Saving…' : 'Save Changes'}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
