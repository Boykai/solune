/**
 * TemplateBrowser — grid of app template cards with category filter.
 * Users can browse templates, filter by category, and select one to start creation.
 */

import { useState } from 'react';
import { cn } from '@/lib/utils';
import type { AppCategory, AppTemplateSummary } from '@/types/app-template';

const CATEGORY_LABELS: Record<AppCategory, string> = {
  saas: 'SaaS',
  api: 'API',
  cli: 'CLI',
  dashboard: 'Dashboard',
};

const CATEGORY_STYLES: Record<AppCategory, string> = {
  saas: 'bg-violet-100/80 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300',
  api: 'bg-sky-100/80 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300',
  cli: 'bg-emerald-100/80 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
  dashboard: 'bg-amber-100/80 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
};

const DIFFICULTY_LABELS: Record<string, string> = {
  S: 'Simple',
  M: 'Medium',
  L: 'Large',
  XL: 'Extra Large',
};

interface TemplateBrowserProps {
  templates: AppTemplateSummary[];
  onSelectTemplate: (templateId: string) => void;
  onAIConfigure?: () => void;
  isLoading?: boolean;
}

export function TemplateBrowser({
  templates,
  onSelectTemplate,
  onAIConfigure,
  isLoading = false,
}: TemplateBrowserProps) {
  const [categoryFilter, setCategoryFilter] = useState<AppCategory | ''>('');

  const filteredTemplates = categoryFilter
    ? templates.filter((t) => t.category === categoryFilter)
    : templates;

  const categories: AppCategory[] = ['saas', 'api', 'cli', 'dashboard'];

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="template-loading">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-48 animate-pulse rounded-xl bg-muted/50" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Category Filter */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setCategoryFilter('')}
          className={cn(
            'rounded-full px-3 py-1 text-sm font-medium transition-colors',
            !categoryFilter
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted/50 text-muted-foreground hover:bg-muted',
          )}
        >
          All
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setCategoryFilter(cat)}
            className={cn(
              'rounded-full px-3 py-1 text-sm font-medium transition-colors',
              categoryFilter === cat
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted/50 text-muted-foreground hover:bg-muted',
            )}
          >
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
        {onAIConfigure && (
          <button
            type="button"
            onClick={onAIConfigure}
            className="ml-auto rounded-full bg-gradient-to-r from-violet-500 to-indigo-500 px-4 py-1 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            ✨ Let AI Configure
          </button>
        )}
      </div>

      {/* Template Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="template-grid">
        {filteredTemplates.map((template) => (
          <div
            key={template.id}
            className="celestial-panel flex flex-col rounded-xl border border-border/80 bg-card/88 p-5 transition-all hover:-translate-y-0.5 hover:shadow-md"
            data-testid={`template-card-${template.id}`}
          >
            <div className="mb-2 flex items-center gap-2">
              <span
                className={cn(
                  'rounded-full px-2 py-0.5 text-xs font-medium',
                  CATEGORY_STYLES[template.category],
                )}
              >
                {CATEGORY_LABELS[template.category]}
              </span>
              <span className="text-xs text-muted-foreground">
                {DIFFICULTY_LABELS[template.difficulty] ?? template.difficulty}
              </span>
            </div>

            <h3 className="mb-1 text-base font-semibold">{template.name}</h3>
            <p className="mb-3 flex-1 text-sm text-muted-foreground">{template.description}</p>

            <div className="mb-3 flex flex-wrap gap-1">
              {template.tech_stack.map((tech) => (
                <span
                  key={tech}
                  className="rounded bg-muted/60 px-1.5 py-0.5 text-xs text-muted-foreground"
                >
                  {tech}
                </span>
              ))}
            </div>

            <button
              type="button"
              onClick={() => onSelectTemplate(template.id)}
              className="w-full rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
              data-testid={`use-template-${template.id}`}
            >
              Use Template
            </button>
          </div>
        ))}
      </div>

      {filteredTemplates.length === 0 && (
        <div className="py-12 text-center text-muted-foreground">
          No templates found for the selected category.
        </div>
      )}
    </div>
  );
}
