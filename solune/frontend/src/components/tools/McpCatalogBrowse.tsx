/**
 * McpCatalogBrowse — inline catalog browse/import section for the Tools page.
 *
 * Lets users search and filter external MCP servers from the Glama catalog,
 * view quality scores and transport types, and import them into the project.
 * Mirrors the AgentsPanel inline catalog pattern.
 */

import { useDeferredValue, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Download,
  ExternalLink,
  Loader2,
  RefreshCw,
  Search,
} from '@/lib/icons';
import { useMcpCatalog, useImportMcpServer } from '@/hooks/useTools';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { CatalogMcpServer } from '@/types';

const CATEGORIES = [
  'Developer Tools',
  'Cloud',
  'Database',
  'Search',
  'Documentation',
  'AI',
  'Communication',
  'Security',
  'Monitoring',
];

interface McpCatalogBrowseProps {
  projectId: string;
}

function QualityBadge({ score }: { score: string | null | undefined }) {
  if (!score) return null;
  const colorMap: Record<string, string> = {
    A: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
    B: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
    C: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  };
  const color = colorMap[score.toUpperCase()] ?? 'bg-muted text-muted-foreground';
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${color}`}>
      {score}
    </span>
  );
}

function TypeBadge({ serverType }: { serverType: string }) {
  const label = serverType === 'stdio' || serverType === 'local' ? 'Local' : 'Remote';
  const color =
    serverType === 'stdio' || serverType === 'local'
      ? 'bg-violet-500/10 text-violet-600 dark:text-violet-400'
      : 'bg-sky-500/10 text-sky-600 dark:text-sky-400';
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${color}`}>
      {label}
    </span>
  );
}

function ServerCard({
  server,
  onImport,
  isImporting,
}: {
  server: CatalogMcpServer;
  onImport: (server: CatalogMcpServer) => void;
  isImporting: boolean;
}) {
  return (
    <article className="celestial-panel flex flex-col justify-between rounded-[1.25rem] border border-border/75 bg-card/95 p-4 shadow-sm transition-colors hover:border-primary/30 hover:bg-background/90">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h5 className="truncate font-medium text-foreground">{server.name}</h5>
          <QualityBadge score={server.quality_score} />
          <TypeBadge serverType={server.server_type} />
        </div>
        <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{server.description}</p>
        {server.category && (
          <p className="mt-1.5 text-[10px] uppercase tracking-wider text-muted-foreground/70">
            {server.category}
          </p>
        )}
      </div>
      <div className="mt-3 flex items-center justify-between gap-2">
        {server.repo_url && (
          <a
            href={server.repo_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            aria-label={`View ${server.name} repository`}
          >
            <ExternalLink className="h-3 w-3" />
            Repo
          </a>
        )}
        <div className="ml-auto">
          {server.already_installed ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-3 w-3" />
              Installed
            </span>
          ) : (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onImport(server)}
              disabled={isImporting}
            >
              {isImporting ? (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              ) : (
                <Download className="mr-1 h-3 w-3" />
              )}
              Import
            </Button>
          )}
        </div>
      </div>
    </article>
  );
}

export function McpCatalogBrowse({ projectId }: McpCatalogBrowseProps) {
  const [searchInput, setSearchInput] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const deferredSearch = useDeferredValue(searchInput);

  const { servers, isLoading, isError, error, refetch } = useMcpCatalog(
    projectId,
    deferredSearch,
    selectedCategory,
  );

  const { importServer, isImporting, importingId } = useImportMcpServer(projectId);

  const handleImport = (server: CatalogMcpServer) => {
    void importServer(server);
  };

  const handleCategoryToggle = (cat: string) => {
    setSelectedCategory((prev) => (prev === cat ? '' : cat));
  };

  return (
    <section
      className="celestial-fade-in ritual-stage rounded-[1.55rem] p-4 sm:rounded-[1.85rem] sm:p-6"
      aria-labelledby="mcp-catalog-title"
    >
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="max-w-3xl">
          <p className="text-[11px] uppercase tracking-[0.24em] text-primary/80">
            MCP Catalog
          </p>
          <h4
            id="mcp-catalog-title"
            className="mt-2 text-[1.35rem] font-display font-medium leading-tight sm:text-[1.6rem]"
          >
            Browse MCP Servers
          </h4>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Discover external MCP servers and import them into your project. Imported servers
            sync to your repository&apos;s MCP configuration.
          </p>
        </div>

        <div className="relative xl:min-w-[22rem]">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search MCP servers…"
            aria-label="Search MCP catalog"
            className="moonwell h-12 rounded-full border-border/60 pl-10"
          />
        </div>
      </div>

      {/* Category filter chips */}
      <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Filter by category">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => handleCategoryToggle(cat)}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              selectedCategory === cat
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border/60 bg-background/60 text-muted-foreground hover:border-primary/40 hover:text-foreground'
            }`}
          >
            {cat}
          </button>
        ))}
        {selectedCategory && (
          <button
            type="button"
            onClick={() => setSelectedCategory('')}
            className="rounded-full border border-border/60 bg-background/60 px-3 py-1 text-xs font-medium text-muted-foreground hover:text-foreground"
          >
            Clear filter
          </button>
        )}
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="mt-6 flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Loading catalog…</span>
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div
          className="celestial-panel mt-6 flex max-w-3xl flex-col items-center justify-center gap-4 rounded-[1.4rem] border border-amber-500/30 bg-background/92 px-6 py-8 text-center shadow-sm"
          role="alert"
        >
          <AlertCircle className="h-6 w-6 text-amber-600 dark:text-amber-400" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">
              MCP catalog is temporarily unavailable.
            </p>
            <p className="text-sm text-muted-foreground">
              Browse catalog is showing an empty list until the upstream source responds again.
            </p>
            {error?.message && (
              <p className="text-xs text-muted-foreground">{error.message}</p>
            )}
          </div>
          <Button variant="outline" size="sm" onClick={() => void refetch()}>
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            Retry
          </Button>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && servers.length === 0 && (
        <div className="mt-6 rounded-[1.25rem] border border-dashed border-border/70 bg-background/78 py-12 text-center text-sm text-muted-foreground">
          {searchInput || selectedCategory
            ? 'No MCP servers match your search.'
            : 'No MCP servers available in the catalog.'}
        </div>
      )}

      {/* Server cards grid */}
      {!isLoading && !isError && servers.length > 0 && (
        <div className="mt-6 grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
          {servers.map((server) => (
            <ServerCard
              key={server.id}
              server={server}
              onImport={handleImport}
              isImporting={isImporting && importingId === server.id}
            />
          ))}
        </div>
      )}
    </section>
  );
}
