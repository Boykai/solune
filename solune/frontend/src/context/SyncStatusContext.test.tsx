import { useEffect } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@/test/test-utils';
import { SyncStatusProvider, useSyncStatusContext } from './SyncStatusContext';

function Consumer({ onRender }: { onRender?: () => void }) {
  const { status, lastUpdate, updateSyncStatus } = useSyncStatusContext();

  useEffect(() => {
    onRender?.();
  });

  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="last-update">{lastUpdate?.toISOString() ?? 'none'}</span>
      <button
        type="button"
        onClick={() => updateSyncStatus('connecting', null)}
      >
        set-connecting
      </button>
      <button
        type="button"
        onClick={() => updateSyncStatus('connected', new Date('2026-04-05T00:00:00.000Z'))}
      >
        set-connected
      </button>
      <button
        type="button"
        onClick={() => updateSyncStatus('connected', new Date('2026-04-05T00:00:00.000Z'))}
      >
        set-connected-same-time
      </button>
    </div>
  );
}

describe('SyncStatusContext', () => {
  it('provides the default state before any updates', () => {
    render(
      <SyncStatusProvider>
        <Consumer />
      </SyncStatusProvider>,
    );

    expect(screen.getByTestId('status')).toHaveTextContent('disconnected');
    expect(screen.getByTestId('last-update')).toHaveTextContent('none');
  });

  it('applies state transitions immediately', async () => {
    render(
      <SyncStatusProvider>
        <Consumer />
      </SyncStatusProvider>,
    );

    await act(async () => {
      screen.getByRole('button', { name: 'set-connecting' }).click();
    });
    expect(screen.getByTestId('status')).toHaveTextContent('connecting');

    await act(async () => {
      screen.getByRole('button', { name: 'set-connected' }).click();
    });

    expect(screen.getByTestId('status')).toHaveTextContent('connected');
    expect(screen.getByTestId('last-update')).toHaveTextContent('2026-04-05T00:00:00.000Z');
  });

  it('deduplicates updates when status and timestamp are value-equal', async () => {
    const onRender = vi.fn();

    render(
      <SyncStatusProvider>
        <Consumer onRender={onRender} />
      </SyncStatusProvider>,
    );

    expect(onRender).toHaveBeenCalledTimes(1);

    await act(async () => {
      screen.getByRole('button', { name: 'set-connected' }).click();
    });
    expect(onRender).toHaveBeenCalledTimes(2);

    await act(async () => {
      screen.getByRole('button', { name: 'set-connected-same-time' }).click();
    });

    expect(onRender).toHaveBeenCalledTimes(2);
  });
});
