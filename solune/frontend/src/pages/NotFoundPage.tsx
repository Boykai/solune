/**
 * NotFoundPage — 404 route fallback.
 */

import { Link, useLocation } from 'react-router-dom';
import { NAV_ROUTES } from '@/constants';
import { getSuggestions } from '@/lib/route-suggestions';

export function NotFoundPage() {
  const { pathname } = useLocation();
  const suggestions = getSuggestions(pathname, NAV_ROUTES);

  return (
    <div className="starfield flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
      <span className="text-6xl font-bold text-primary/30 celestial-float">404</span>
      <h1 className="text-4xl font-display font-medium tracking-[0.06em] celestial-fade-in">
        Lost Between Sun & Moon
      </h1>
      <p className="max-w-md text-muted-foreground">
        The page you’re looking for drifted out of orbit. Return home to rejoin the main
        constellation.
      </p>

      {suggestions.length > 0 && (
        <div className="mt-2 flex flex-col items-center gap-2">
          <p className="text-sm font-medium text-muted-foreground">Did you mean?</p>
          <div className="flex flex-wrap justify-center gap-2">
            {suggestions.map((route) => {
              const Icon = route.icon;
              return (
                <Link
                  key={route.path}
                  to={route.path}
                  className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-card/80 px-4 py-2 text-sm font-medium text-foreground shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                >
                  <Icon className="h-4 w-4 text-primary" />
                  {route.label}
                </Link>
              );
            })}
          </div>
        </div>
      )}

      <Link
        to="/"
        className="mt-2 rounded-full bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground shadow-sm transition-all hover:-translate-y-0.5 hover:bg-primary/90 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        Go Home
      </Link>
    </div>
  );
}
