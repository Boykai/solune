import { useId, useState, type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { BarChart3 } from '@/lib/icons';

export interface CompactPageHeaderStat {
  label: string;
  value: string;
}

export interface CompactPageHeaderProps {
  eyebrow: string;
  title: string;
  description: string;
  badge?: string;
  stats?: CompactPageHeaderStat[];
  actions?: ReactNode;
  className?: string;
}

export function CompactPageHeader({
  eyebrow,
  title,
  description,
  badge,
  stats = [],
  actions,
  className,
}: CompactPageHeaderProps) {
  const [mobileStatsOpen, setMobileStatsOpen] = useState(false);
  const statsId = useId();

  return (
    <header
      className={cn(
        'rounded-2xl border border-border/70 bg-background/60 px-4 py-3 backdrop-blur-sm sm:px-6 sm:py-4',
        className,
      )}
    >
      <div className="flex flex-col gap-3 md:grid md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] md:items-start md:gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] uppercase tracking-[0.28em] text-primary/85">{eyebrow}</p>

          <h2 className="mt-1 text-xl font-semibold leading-tight tracking-tight text-foreground sm:text-2xl">
            {title}
          </h2>

          {/* Description: single-line truncated, expands on hover */}
          <div className="group">
            <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground line-clamp-1 group-hover:line-clamp-none">
              {description}
            </p>
          </div>
        </div>

        {badge && (
          <div className="min-w-0 md:col-start-2 md:justify-self-center">
            <span className="inline-flex max-w-[12rem] items-center truncate rounded-full border border-primary/25 bg-primary/10 px-2.5 py-0.5 text-[10px] uppercase tracking-[0.18em] text-primary">
              {badge}
            </span>
          </div>
        )}

        {actions && (
          <div className="flex shrink-0 flex-wrap items-center gap-2 md:col-start-3 md:justify-self-end">
            {actions}
          </div>
        )}
      </div>

      {stats.length > 0 && (
        <div className="mt-2">
          <button
            type="button"
            className="flex items-center gap-1.5 text-xs text-muted-foreground md:hidden"
            onClick={() => setMobileStatsOpen((prev) => !prev)}
            aria-expanded={mobileStatsOpen}
            aria-controls={statsId}
          >
            <BarChart3 className="h-3.5 w-3.5" />
            {mobileStatsOpen ? 'Hide stats' : 'Show stats'}
          </button>

          <div
            id={statsId}
            className={cn(
              'flex flex-wrap items-center gap-2',
              mobileStatsOpen ? 'mt-2' : 'hidden md:flex',
            )}
          >
            {stats.map((stat) => (
              <span
                key={stat.label}
                className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-muted/40 px-2.5 py-1 text-xs"
              >
                <span className="text-muted-foreground">{stat.label}</span>
                <span className="min-w-0 max-w-[8rem] truncate font-medium text-foreground">{stat.value}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </header>
  );
}
