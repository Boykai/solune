/**
 * PageTransition — wraps <Outlet /> with a subtle fade-in on route changes.
 * Uses key={pathname} so React remounts the wrapper on navigation,
 * triggering the CSS page-enter animation. Respects prefers-reduced-motion
 * via the Tailwind motion-safe: prefix.
 *
 * Also restores scroll position to the top of <main> on every route change
 * so users never land mid-page after navigating.
 */

import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';

export function PageTransition() {
  const { pathname } = useLocation();

  useEffect(() => {
    const main = document.querySelector('main');
    if (main) main.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div key={pathname} className="motion-safe:animate-page-enter">
      <Outlet />
    </div>
  );
}
