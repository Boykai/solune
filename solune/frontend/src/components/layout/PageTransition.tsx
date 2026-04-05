/**
 * PageTransition — wraps <Outlet /> with a subtle fade-in on route changes.
 * Uses key={pathname} so React remounts the wrapper on navigation,
 * triggering the CSS page-enter animation. Respects prefers-reduced-motion
 * via the Tailwind motion-safe: prefix.
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
