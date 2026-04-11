import { describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

const mocks = vi.hoisted(() => ({
  list: vi.fn().mockResolvedValue({
    conversations: [
      {
        conversation_id: 'conv-1',
        session_id: 'sess-1',
        title: 'Chat 1',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ],
  }),
  create: vi.fn().mockResolvedValue({
    conversation_id: 'conv-new',
    session_id: 'sess-1',
    title: 'New Chat',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }),
  update: vi.fn().mockResolvedValue({
    conversation_id: 'conv-1',
    session_id: 'sess-1',
    title: 'Updated Title',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T01:00:00Z',
  }),
  delete: vi.fn().mockResolvedValue({ message: 'Deleted' }),
}));

vi.mock('@/services/api', () => ({
  conversationApi: mocks,
}));

import { useConversations } from '@/hooks/useConversations';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('useConversations', () => {
  it('returns conversations from the API', async () => {
    const { result } = renderHook(() => useConversations(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.conversations).toHaveLength(1);
    });
    expect(result.current.conversations[0].title).toBe('Chat 1');
  });

  it('creates a conversation', async () => {
    const { result } = renderHook(() => useConversations(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const conv = await result.current.createConversation('Test');
    expect(conv.conversation_id).toBe('conv-new');
    expect(mocks.create).toHaveBeenCalledWith('Test');
  });

  it('updates a conversation', async () => {
    const { result } = renderHook(() => useConversations(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await result.current.updateConversation('conv-1', 'New Name');
    expect(mocks.update).toHaveBeenCalledWith('conv-1', 'New Name');
  });

  it('deletes a conversation', async () => {
    const { result } = renderHook(() => useConversations(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await result.current.deleteConversation('conv-1');
    expect(mocks.delete).toHaveBeenCalledWith('conv-1');
  });

  it('returns empty conversations when API returns empty list', async () => {
    mocks.list.mockResolvedValueOnce({ conversations: [] });
    const { result } = renderHook(() => useConversations(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.conversations).toEqual([]);
  });

  it('exposes loading state during initial fetch', () => {
    // Make the list call hang indefinitely for this test
    mocks.list.mockReturnValueOnce(new Promise(() => {}));
    const { result } = renderHook(() => useConversations(), { wrapper: createWrapper() });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.conversations).toEqual([]);
  });

  it('exposes error when list fails', async () => {
    mocks.list.mockRejectedValueOnce(new Error('Network error'));
    const { result } = renderHook(() => useConversations(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error?.message).toBe('Network error');
  });

  it('creates conversation with default title when no title provided', async () => {
    const { result } = renderHook(() => useConversations(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await result.current.createConversation();
    expect(mocks.create).toHaveBeenCalledWith(undefined);
  });
});
