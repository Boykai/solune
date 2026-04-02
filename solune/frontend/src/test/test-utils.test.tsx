/**
 * Regression tests for shared test utilities.
 *
 * Ensures `renderWithProviders()` wraps components correctly and
 * `createTestQueryClient()` returns a well-configured client.
 */

import { describe, expect, it } from 'vitest';
import { renderWithProviders, createTestQueryClient } from './test-utils';

describe('renderWithProviders', () => {
  it('renders children exactly once', () => {
    const { container } = renderWithProviders(
      <div data-testid="unique-child">hello</div>
    );
    const children = container.querySelectorAll('[data-testid="unique-child"]');
    expect(children).toHaveLength(1);
  });

  it('exposes the queryClient used for rendering', () => {
    const { queryClient } = renderWithProviders(<div />);
    expect(queryClient).toBeDefined();
    expect(queryClient.getDefaultOptions().queries?.retry).toBe(false);
  });

  it('accepts a custom queryClient', () => {
    const custom = createTestQueryClient();
    const { queryClient } = renderWithProviders(<div />, {
      queryClient: custom,
    });
    expect(queryClient).toBe(custom);
  });
});

describe('createTestQueryClient', () => {
  it('disables retries for queries and mutations', () => {
    const client = createTestQueryClient();
    const defaults = client.getDefaultOptions();
    expect(defaults.queries?.retry).toBe(false);
    expect(defaults.mutations?.retry).toBe(false);
  });

  it('disables refetch on window focus', () => {
    const client = createTestQueryClient();
    expect(client.getDefaultOptions().queries?.refetchOnWindowFocus).toBe(
      false
    );
  });

  it('sets gcTime to Infinity so cache survives the test', () => {
    const client = createTestQueryClient();
    expect(client.getDefaultOptions().queries?.gcTime).toBe(Infinity);
  });
});
