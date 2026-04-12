import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface CompactPageHeaderStat {
  label: string;
  value: string;
}

interface CompactPageHeaderProps {
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
  return (
    <section
      className={cn(
        'section-aurora relative overflow-hidden rounded-2xl border border-border/70 px-5 py-4 shadow-sm sm:rounded-[1.6rem] sm:px-6 sm:py-5',
        className
      )}
    >
      <div className="relative z-10 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[10px] uppercase tracking-[0.28em] text-primary/80">{eyebrow}</p>
            {badge && (
              <span className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-0.5 text-[10px] uppercase tracking-[0.18em] text-primary">
                {badge}
              </span>
            )}
          </div>
          <h2 className="mt-1.5 text-xl font-display font-medium leading-tight tracking-[0.01em] text-foreground sm:text-2xl">
            {title}
          </h2>
          <p className="mt-1 line-clamp-1 text-xs leading-5 text-muted-foreground sm:text-sm">
            {description}
          </p>
        </div>

        {(stats.length > 0 || actions) && (
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            {stats.map((stat) => (
              <span
                key={stat.label}
                className="moonwell inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs"
              >
                <span className="text-muted-foreground/70">{stat.label}</span>
                <span className="font-semibold text-foreground">{stat.value}</span>
              </span>
            ))}
            {actions && (
              <div className="flex items-center gap-2">{actions}</div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
