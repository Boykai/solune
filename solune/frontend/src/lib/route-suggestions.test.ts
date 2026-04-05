import { describe, expect, it } from 'vitest';
import type { NavRoute } from '@/types';
import { getSuggestions } from './route-suggestions';

const routes: NavRoute[] = [
  { path: '/agents', label: 'Agents', icon: () => null },
  { path: '/board', label: 'Board', icon: () => null },
  { path: '/settings', label: 'Settings', icon: () => null },
  { path: '/pipelines', label: 'Pipelines', icon: () => null },
];

describe('getSuggestions', () => {
  it('returns the closest matching route first', () => {
    const suggestions = getSuggestions('/agnts', routes);

    expect(suggestions.map((route) => route.path)).toEqual(['/agents']);
  });

  it('applies the threshold filter', () => {
    const suggestions = getSuggestions('/totally-different', routes, { threshold: 2 });

    expect(suggestions).toEqual([]);
  });

  it('returns multiple matches ordered by relevance and limited by the requested size', () => {
    const suggestions = getSuggestions('/boardd', routes, { limit: 2, threshold: 6 });

    expect(suggestions).toHaveLength(2);
    expect(suggestions[0].path).toBe('/board');
  });

  it('returns an empty array for empty input', () => {
    expect(getSuggestions('', routes)).toEqual([]);
    expect(getSuggestions('///', routes)).toEqual([]);
  });

  it('returns an empty array when there are no candidate routes', () => {
    expect(getSuggestions('/agents', [])).toEqual([]);
  });
});
