/**
 * BrowseAgentsModal — dedicated modal for browsing and importing Awesome Copilot agents.
 *
 * Displays a searchable list of catalog agents fetched from the cached llms.txt index.
 * Users can import agents with a single click; already-imported agents are marked.
 */

import { useMemo, useState } from 'react';
import { Search, Download, CheckCircle2, Loader2, AlertCircle } from '@/lib/icons';
import { useCatalogAgents, useImportAgent } from '@/hooks/useAgents';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { CatalogAgent } from '@/services/api';

interface BrowseAgentsModalProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function BrowseAgentsModal({ projectId, isOpen, onClose }: BrowseAgentsModalProps) {
  const [search, setSearch] = useState('');
  const { data: catalogAgents, isLoading, isError } = useCatalogAgents(isOpen ? projectId : null);
  const importMutation = useImportAgent(projectId);
  const [importingId, setImportingId] = useState<string | null>(null);

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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="relative flex max-h-[80vh] w-full max-w-2xl flex-col rounded-2xl bg-[var(--color-bg-card)] shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--color-border)] p-6">
          <div>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">
              Browse Awesome Copilot Agents
            </h2>
            <p className="text-sm text-[var(--color-text-muted)]">
              Import agents from the Awesome Copilot catalog into your project
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text)]"
            aria-label="Close browse modal"
          >
            ✕
          </button>
        </div>

        {/* Search */}
        <div className="border-b border-[var(--color-border)] p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <Input
              placeholder="Search agents…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-[var(--color-text-muted)]" />
              <span className="ml-2 text-sm text-[var(--color-text-muted)]">Loading catalog…</span>
            </div>
          )}

          {isError && (
            <div className="flex items-center justify-center gap-2 py-12 text-sm text-[var(--color-text-muted)]">
              <AlertCircle className="h-5 w-5" />
              <span>Failed to load catalog. Please try again.</span>
            </div>
          )}

          {!isLoading && !isError && filteredAgents.length === 0 && (
            <div className="py-12 text-center text-sm text-[var(--color-text-muted)]">
              {search ? 'No agents match your search.' : 'No agents available in the catalog.'}
            </div>
          )}

          {!isLoading && !isError && filteredAgents.length > 0 && (
            <div className="space-y-2">
              {filteredAgents.map((agent) => (
                <div
                  key={agent.id}
                  className="flex items-center justify-between rounded-xl border border-[var(--color-border)] p-4 transition-colors hover:bg-[var(--color-bg-hover)]"
                >
                  <div className="min-w-0 flex-1">
                    <h3 className="font-medium text-[var(--color-text)]">{agent.name}</h3>
                    <p className="mt-0.5 text-sm text-[var(--color-text-muted)] line-clamp-2">
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
        <div className="flex justify-end border-t border-[var(--color-border)] p-4">
          <Button variant="outline" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
    </div>
  );
}
