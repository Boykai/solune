/**
 * BrowseAgentsModal — dedicated modal for browsing and importing Awesome Copilot agents.
 *
 * Displays a searchable list of catalog agents fetched from the cached llms.txt index.
 * Users can import agents with a single click; already-imported agents are marked.
 */

import { useMemo, useState } from 'react';
import { Search, Download, CheckCircle2, Loader2, AlertCircle } from '@/lib/icons';
import { ApiError, type CatalogAgent } from '@/services/api';
import { useCatalogAgents, useImportAgent } from '@/hooks/useAgents';
import { getErrorMessage } from '@/hooks/useApps';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface BrowseAgentsModalProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function BrowseAgentsModal({ projectId, isOpen, onClose }: BrowseAgentsModalProps) {
  const [search, setSearch] = useState('');
  const { data: catalogAgents, error, isLoading, isError, refetch } = useCatalogAgents(
    isOpen ? projectId : null
  );
  const importMutation = useImportAgent(projectId);
  const [importingId, setImportingId] = useState<string | null>(null);

  const catalogErrorMessage = getErrorMessage(
    error,
    'Browser Agents catalog is temporarily unavailable.'
  );
  const catalogErrorReason =
    error instanceof ApiError && typeof error.error.details?.reason === 'string'
      ? error.error.details.reason
      : null;

  const filteredAgents = useMemo(() => {
    if (!catalogAgents) return [];
    if (!search.trim()) return catalogAgents;
    const q = search.toLowerCase();
    return catalogAgents.filter(
      (agent) =>
        agent.name.toLowerCase().includes(q) || agent.description.toLowerCase().includes(q)
    );
  }, [catalogAgents, search]);

  const handleImport = async (agent: CatalogAgent) => {
    setImportingId(agent.id);
    try {
      await importMutation.mutateAsync({
        catalog_agent_id: agent.id,
        name: agent.name,
        description: agent.description,
        source_url: agent.source_url,
      });
    } finally {
      setImportingId(null);
    }
  };

  const handleBackdropClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm"
      role="presentation"
      onClick={handleBackdropClick}
    >
      <div className="flex min-h-full items-center justify-center p-4 sm:p-6">
        <div
          className="celestial-panel celestial-fade-in relative flex max-h-[min(88vh,56rem)] w-full max-w-2xl flex-col overflow-hidden rounded-[1.5rem] border border-border/80 bg-card shadow-xl"
          role="dialog"
          aria-modal="true"
          aria-labelledby="browse-agents-title"
          onClick={(event) => event.stopPropagation()}
        >
        {/* Header */}
        <div className="flex items-center justify-between gap-4 border-b border-border/70 px-5 py-5 sm:px-6">
          <div>
            <h2 id="browse-agents-title" className="text-lg font-semibold text-foreground">
              Browse Awesome Copilot Agents
            </h2>
            <p className="text-sm text-muted-foreground">
              Import agents from the Awesome Copilot catalog into your project
            </p>
          </div>
          <button
            onClick={onClose}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-background/75 text-muted-foreground transition-colors hover:bg-background hover:text-foreground"
            aria-label="Close browse modal"
          >
            ✕
          </button>
        </div>

        {/* Search */}
        <div className="border-b border-border/70 bg-background/72 px-5 py-4 sm:px-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search agents…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="border-border/70 bg-background/90 pl-10"
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto bg-background/50 px-5 py-4 sm:px-6">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-2 text-sm text-muted-foreground">Loading catalog…</span>
            </div>
          )}

          {isError && (
            <div
              className="celestial-panel mx-auto flex max-w-lg flex-col items-center justify-center gap-4 rounded-[1.4rem] border border-amber-500/30 bg-background/92 px-6 py-8 text-center shadow-sm"
              role="alert"
            >
              <AlertCircle className="h-6 w-6 text-amber-600 dark:text-amber-400" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">
                  {catalogErrorMessage}
                </p>
                <p className="text-sm text-muted-foreground">
                  Browser Agents is showing an empty catalog until the upstream source
                  responds again.
                </p>
                {catalogErrorReason && (
                  <p className="text-xs text-muted-foreground">{catalogErrorReason}</p>
                )}
              </div>
              <Button variant="outline" size="sm" onClick={() => void refetch()}>
                Retry
              </Button>
            </div>
          )}

          {!isLoading && !isError && filteredAgents.length === 0 && (
            <div className="rounded-[1.25rem] border border-dashed border-border/70 bg-background/78 py-12 text-center text-sm text-muted-foreground">
              {search ? 'No agents match your search.' : 'No agents available in the catalog.'}
            </div>
          )}

          {!isLoading && !isError && filteredAgents.length > 0 && (
            <div className="space-y-3">
              {filteredAgents.map((agent) => (
                <div
                  key={agent.id}
                  className="celestial-panel flex items-center justify-between rounded-[1.25rem] border border-border/75 bg-card/95 p-4 shadow-sm transition-colors hover:border-primary/30 hover:bg-background/90"
                >
                  <div className="min-w-0 flex-1">
                    <h3 className="font-medium text-foreground">{agent.name}</h3>
                    <p className="mt-0.5 line-clamp-2 text-sm text-muted-foreground">
                      {agent.description}
                    </p>
                  </div>
                  <div className="ml-4 flex-shrink-0">
                    {agent.already_imported ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-600 dark:text-amber-400">
                        <CheckCircle2 className="h-3 w-3" />
                        Imported
                      </span>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void handleImport(agent)}
                        disabled={importingId === agent.id}
                      >
                        {importingId === agent.id ? (
                          <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                        ) : (
                          <Download className="mr-1 h-3 w-3" />
                        )}
                        Import
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end border-t border-border/70 bg-background/72 px-5 py-4 sm:px-6">
          <Button variant="outline" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
      </div>
    </div>
  );
}
