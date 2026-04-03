import { TriangleAlert } from '@/lib/icons';

/**
 * Dynamic dropdown component for model selection.
 *
 * Handles all states: idle, loading, success, error, auth_required, rate_limited.
 * Shows loading spinner, error messages with retry, cache freshness indicator,
 * and prerequisite messages.
 *
 * When models support reasoning levels, the dropdown expands them into per-level
 * variants (e.g., "o3 (High)"). The `onReasoningEffortChange` callback reports
 * the selected reasoning level separately.
 */

import { type ModelOption, type ModelsResponse } from '@/types';
import { formatTimeAgo } from '@/utils/formatTime';
import { formatReasoningLabel } from '@/hooks/useModels';

/** Expand reasoning-capable models into per-level variants. */
function expandModelsForDropdown(models: ModelOption[]): (ModelOption & { reasoning_effort?: string })[] {
  const expanded: (ModelOption & { reasoning_effort?: string })[] = [];
  for (const m of models) {
    if (m.supported_reasoning_efforts?.length) {
      for (const level of m.supported_reasoning_efforts) {
        expanded.push({
          ...m,
          id: m.id,
          name: `${m.name} (${formatReasoningLabel(level)})`,
          reasoning_effort: level,
        });
      }
    } else {
      expanded.push(m);
    }
  }
  return expanded;
}

interface DynamicDropdownProps {
  /** Current selected value */
  value: string;
  /** Change handler */
  onChange: (value: string) => void;
  /** Provider name for labeling */
  provider: string | undefined;
  /** Whether the provider supports dynamic model fetching */
  supportsDynamic: boolean;
  /** Response from useModelOptions hook */
  modelsResponse: ModelsResponse | undefined;
  /** Whether the query is loading */
  isLoading: boolean;
  /** Retry handler */
  onRetry: () => void;
  /** Label for the dropdown */
  label: string;
  /** HTML id attribute */
  id: string;
  /** Static fallback options (for providers without dynamic fetching) */
  staticOptions?: { id: string; name: string }[];
  /** Called when a reasoning model variant is selected */
  onReasoningEffortChange?: (effort: string) => void;
  /** Current reasoning effort for highlighting the selected variant */
  reasoningEffort?: string;
}


const selectClass =
  'celestial-focus flex h-9 w-full rounded-md border border-input bg-background/72 text-foreground px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed';

export function DynamicDropdown({
  value,
  onChange,
  provider,
  supportsDynamic,
  modelsResponse,
  isLoading,
  onRetry,
  label,
  id,
  staticOptions,
  onReasoningEffortChange,
  reasoningEffort,
}: DynamicDropdownProps) {
  // Non-dynamic provider: render static options
  if (!supportsDynamic || !provider) {
    return (
      <div className="flex flex-col gap-2">
        <label htmlFor={id} className="text-sm font-medium text-foreground">
          {label}
        </label>
        {staticOptions && staticOptions.length > 0 ? (
          <select
            id={id}
            className={selectClass}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            aria-label={label}
          >
            <option value="">Select a model</option>
            {staticOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.name}
              </option>
            ))}
          </select>
        ) : (
          <input
            id={id}
            type="text"
            className="celestial-focus flex h-9 w-full rounded-md border border-input bg-background/72 px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="e.g. gpt-4o"
            aria-label={label}
          />
        )}
      </div>
    );
  }

  const status = modelsResponse?.status;
  const rawModels = modelsResponse?.models ?? [];
  const expandedModels = expandModelsForDropdown(rawModels);
  const fetchedAt = modelsResponse?.fetched_at;
  const message = modelsResponse?.message;
  const rateLimitWarning = modelsResponse?.rate_limit_warning;

  /** Encode model id + reasoning effort into a single option value. */
  const encodeValue = (modelId: string, effort?: string) =>
    effort ? `${modelId}::${effort}` : modelId;

  /** Decode a composite option value back to model id + reasoning effort. */
  const handleModelChange = (optionValue: string) => {
    const separatorIdx = optionValue.indexOf('::');
    if (separatorIdx !== -1) {
      const modelId = optionValue.slice(0, separatorIdx);
      const effort = optionValue.slice(separatorIdx + 2);
      onChange(modelId);
      onReasoningEffortChange?.(effort);
    } else {
      onChange(optionValue);
      onReasoningEffortChange?.('');
    }
  };

  /** Compute the current composite value for the select element.
   *
   * Backward-compat: if a reasoning-capable model is selected but no
   * reasoning effort is stored (pre-reasoning settings), fall back to the
   * model's default reasoning effort so the select control has a valid match.
   */
  const resolvedEffort = (() => {
    if (reasoningEffort) return reasoningEffort;
    if (!value) return undefined;
    const matchedRaw = rawModels.find((m) => m.id === value);
    if (matchedRaw?.supported_reasoning_efforts?.length && matchedRaw.default_reasoning_effort) {
      return matchedRaw.default_reasoning_effort;
    }
    return undefined;
  })();
  const compositeValue = encodeValue(value, resolvedEffort);

  // Loading state
  if (isLoading && !modelsResponse) {
    return (
      <div className="flex flex-col gap-2">
        <label htmlFor={id} className="text-sm font-medium text-foreground">
          {label}
        </label>
        <div className="relative" aria-busy="true" aria-label={`Loading ${label}`}>
          <select id={id} className={selectClass} disabled aria-label={`${label} - loading`}>
            <option>Loading models...</option>
          </select>
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-border border-t-primary rounded-full animate-spin" />
          </div>
        </div>
        <div aria-live="polite" className="sr-only">
          Loading available models
        </div>
      </div>
    );
  }

  // Auth required state
  if (status === 'auth_required') {
    return (
      <div className="flex flex-col gap-2">
        <label htmlFor={id} className="text-sm font-medium text-foreground">
          {label}
        </label>
        <div
          className="flex items-center gap-2 rounded-md border border-primary/25 bg-primary/10 p-3 text-sm text-foreground"
          role="status"
        >
          <TriangleAlert className="h-4 w-4 shrink-0 text-primary" />
          <span>{message || 'Authentication required to fetch models'}</span>
        </div>
      </div>
    );
  }

  // Error state (with possible cached fallback)
  if (status === 'error') {
    return (
      <div className="flex flex-col gap-2">
        <label htmlFor={id} className="text-sm font-medium text-foreground">
          {label}
        </label>
        {expandedModels.length > 0 ? (
          <select
            id={id}
            className={selectClass}
            value={compositeValue}
            onChange={(e) => handleModelChange(e.target.value)}
            aria-label={label}
          >
            <option value="">Select a model</option>
            {expandedModels.map((m) => {
              const key = encodeValue(m.id, m.reasoning_effort);
              return (
                <option key={key} value={key}>
                  {m.name}
                </option>
              );
            })}
          </select>
        ) : null}
        <div
          className="flex items-center justify-between gap-2 p-3 rounded-md border border-destructive/50 bg-destructive/10 text-sm text-destructive"
          role="alert"
        >
          <span>{message || 'Failed to fetch models'}</span>
          <button
            type="button"
            className="celestial-focus shrink-0 px-3 py-1 text-xs font-medium bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90 transition-colors focus-visible:outline-none"
            onClick={onRetry}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Rate limited state
  if (status === 'rate_limited') {
    return (
      <div className="flex flex-col gap-2">
        <label htmlFor={id} className="text-sm font-medium text-foreground">
          {label}
        </label>
        {expandedModels.length > 0 ? (
          <select
            id={id}
            className={selectClass}
            value={compositeValue}
            onChange={(e) => handleModelChange(e.target.value)}
            aria-label={label}
          >
            <option value="">Select a model</option>
            {expandedModels.map((m) => {
              const key = encodeValue(m.id, m.reasoning_effort);
              return (
                <option key={key} value={key}>
                  {m.name}
                </option>
              );
            })}
          </select>
        ) : null}
        <div
          className="flex items-center gap-2 rounded-md bg-primary/10 p-2 text-xs text-foreground"
          role="status"
        >
          <span className="inline-flex items-center gap-2">
            <TriangleAlert className="h-3.5 w-3.5" />
            {message || 'Rate limit reached. Using cached values.'}
          </span>
        </div>
      </div>
    );
  }

  // Success state (possibly with rate limit warning)
  const hasModels = expandedModels.length > 0;

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium text-foreground">
        {label}
      </label>
      {hasModels ? (
        <select
          id={id}
          className={selectClass}
          value={compositeValue}
          onChange={(e) => handleModelChange(e.target.value)}
          aria-label={label}
        >
          <option value="">Select a model</option>
          {expandedModels.map((m) => {
            const key = encodeValue(m.id, m.reasoning_effort);
            return (
              <option key={key} value={key}>
                {m.name}
              </option>
            );
          })}
        </select>
      ) : (
        <div
          className="flex items-center gap-2 rounded-md border border-border bg-background/52 p-3 text-sm text-muted-foreground"
          role="status"
        >
          No models available for this provider
        </div>
      )}
      {/* Freshness indicator */}
      <div className="flex items-center gap-2" aria-live="polite">
        {fetchedAt && (
          <span className="text-xs text-muted-foreground">
            Last updated {formatTimeAgo(new Date(fetchedAt))}
          </span>
        )}
        {rateLimitWarning && (
          <span className="inline-flex items-center gap-1 text-xs text-accent-foreground">
            <TriangleAlert className="h-3.5 w-3.5" />
            API rate limit approaching
          </span>
        )}
        {isLoading && (
          <div className="w-3 h-3 border-2 border-border border-t-primary rounded-full animate-spin" />
        )}
      </div>
    </div>
  );
}
