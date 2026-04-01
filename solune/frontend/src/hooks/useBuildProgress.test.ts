import type { RefObject } from 'react';
import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useBuildProgress } from './useBuildProgress';

class MockWebSocket extends EventTarget {
  emitMessage(payload: unknown) {
    this.dispatchEvent(new MessageEvent('message', { data: JSON.stringify(payload) }));
  }

  emitRawMessage(data: string) {
    this.dispatchEvent(new MessageEvent('message', { data }));
  }
}

function createWsRef(socket: MockWebSocket): RefObject<WebSocket | null> {
  return { current: socket as unknown as WebSocket };
}

describe('useBuildProgress', () => {
  it('ignores malformed and unrelated websocket messages', () => {
    const socket = new MockWebSocket();
    const { result } = renderHook(() => useBuildProgress('stock-dashboard', createWsRef(socket)));

    act(() => {
      socket.emitRawMessage('{not-json');
      socket.emitMessage({
        type: 'build_progress',
        app_name: 'other-app',
        phase: 'scaffolding',
        agent_name: 'architect',
        detail: 'Wrong app',
        pct_complete: 20,
        updated_at: '2026-03-31T00:00:00Z',
      });
    });

    expect(result.current.progress).toBeNull();
    expect(result.current.milestones).toEqual([]);
    expect(result.current.completion).toBeNull();
    expect(result.current.failure).toBeNull();
    expect(result.current.isActive).toBe(false);
  });

  it('tracks progress updates for the selected app', () => {
    const socket = new MockWebSocket();
    const { result } = renderHook(() => useBuildProgress('stock-dashboard', createWsRef(socket)));

    act(() => {
      socket.emitMessage({
        type: 'build_progress',
        app_name: 'stock-dashboard',
        phase: 'configuring',
        agent_name: 'architect',
        detail: 'Preparing pipeline',
        pct_complete: 40,
        updated_at: '2026-03-31T00:00:00Z',
      });
    });

    expect(result.current.progress).toMatchObject({
      phase: 'configuring',
      agent_name: 'architect',
      detail: 'Preparing pipeline',
      pct_complete: 40,
    });
    expect(result.current.isActive).toBe(true);
  });

  it('appends matching milestone events in order', () => {
    const socket = new MockWebSocket();
    const { result } = renderHook(() => useBuildProgress('stock-dashboard', createWsRef(socket)));

    act(() => {
      socket.emitMessage({
        type: 'build_milestone',
        app_name: 'stock-dashboard',
        milestone: 'scaffolded',
        message: 'Scaffold ready',
        updated_at: '2026-03-31T00:00:00Z',
      });
      socket.emitMessage({
        type: 'build_milestone',
        app_name: 'stock-dashboard',
        milestone: 'review',
        message: 'Ready for review',
        updated_at: '2026-03-31T00:01:00Z',
      });
    });

    expect(result.current.milestones.map((milestone) => milestone.milestone)).toEqual([
      'scaffolded',
      'review',
    ]);
  });

  it('captures completion and failure events for the selected app', () => {
    const socket = new MockWebSocket();
    const { result } = renderHook(() => useBuildProgress('stock-dashboard', createWsRef(socket)));

    act(() => {
      socket.emitMessage({
        type: 'build_complete',
        app_name: 'stock-dashboard',
        message: 'Build finished',
        links: { repo_url: 'https://github.com/Boykai/solune' },
        updated_at: '2026-03-31T00:00:00Z',
      });
      socket.emitMessage({
        type: 'build_failed',
        app_name: 'stock-dashboard',
        phase: 'building',
        message: 'CI failed',
        updated_at: '2026-03-31T00:01:00Z',
      });
    });

    expect(result.current.completion).toMatchObject({
      message: 'Build finished',
      links: { repo_url: 'https://github.com/Boykai/solune' },
    });
    expect(result.current.failure).toMatchObject({
      phase: 'building',
      message: 'CI failed',
    });
  });
});
