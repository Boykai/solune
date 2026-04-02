/**
 * Breadcrumb — derives breadcrumb segments from the current pathname, NAV_ROUTES,
 * and dynamic label overrides provided via BreadcrumbContext.
 */

import { useLocation, Link } from 'react-router-dom';
import { NAV_ROUTES } from '@/constants';
import { ChevronRight } from '@/lib/icons';
import { useBreadcrumbLabels } from '@/hooks/useBreadcrumb';
import { buildBreadcrumbSegments } from '@/lib/breadcrumb-utils';

export function Breadcrumb() {
  const { pathname } = useLocation();
  const labelOverrides = useBreadcrumbLabels();
  const segments = buildBreadcrumbSegments(pathname, NAV_ROUTES, labelOverrides);

  return (
    <nav aria-label="Breadcrumb" className="flex min-w-0 max-w-full items-center gap-1 overflow-hidden text-sm text-muted-foreground">
      {segments.map((segment, i) => (
        <span key={segment.path} className="flex min-w-0 items-center gap-1">
          {i > 0 && <ChevronRight className="w-3.5 h-3.5 shrink-0 text-primary/60" />}
          {i < segments.length - 1 ? (
            <Link to={segment.path} className="max-w-[120px] truncate transition-colors hover:text-primary sm:max-w-[200px]">
              {segment.label}
            </Link>
          ) : (
            <span className="max-w-[150px] truncate font-medium tracking-wide text-foreground sm:max-w-[250px]">{segment.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
