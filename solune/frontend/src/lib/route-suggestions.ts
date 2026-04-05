/**
 * route-suggestions — fuzzy-match a pathname against NAV_ROUTES
 * to power "Did you mean …?" on the 404 page.
 */

import type { NavRoute } from '@/types';

/** Levenshtein distance between two strings. */
function levenshtein(a: string, b: string): number {
  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array<number>(n + 1).fill(0));

  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] =
        a[i - 1] === b[j - 1]
          ? dp[i - 1][j - 1]
          : 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
    }
  }
  return dp[m][n];
}

/**
 * Return up to `limit` route suggestions sorted by Levenshtein distance.
 * Only routes whose distance is ≤ `threshold` are included.
 */
export function getSuggestions(
  pathname: string,
  routes: NavRoute[],
  { limit = 3, threshold = 4 } = {},
): NavRoute[] {
  const input = pathname.toLowerCase().replace(/^\/+|\/+$/g, '');
  if (!input || routes.length === 0) {
    return [];
  }

  return routes
    .map((r) => ({ route: r, dist: levenshtein(input, r.path.replace(/^\//, '')) }))
    .filter((r) => r.dist <= threshold && r.dist > 0)
    .sort((a, b) => a.dist - b.dist)
    .slice(0, limit)
    .map((r) => r.route);
}
