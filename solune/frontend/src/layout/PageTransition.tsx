/**
 * PageTransition — wraps routed page content with a subtle fade-in on pathname changes.
 * Respects reduced motion via the shared `motion-safe` animation token.
 */

import { Outlet, useLocation } from 'react-router-dom';

export function PageTransition() {
  const { pathname } = useLocation();

  return (
    <div key={pathname} className="motion-safe:animate-page-enter">
      <Outlet />
    </div>
  );
}