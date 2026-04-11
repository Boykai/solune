/**
 * useConversations hook — manages conversation CRUD with React Query.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { conversationApi } from '@/services/api';
import { STALE_TIME_MEDIUM } from '@/constants';

export function useConversations() {
  const queryClient = useQueryClient();

  const {
    data: conversationsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['conversations'],
    queryFn: conversationApi.list,
    staleTime: STALE_TIME_MEDIUM,
  });

  const createMutation = useMutation({
    mutationFn: (title?: string) => conversationApi.create(title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ conversationId, title }: { conversationId: string; title: string }) =>
      conversationApi.update(conversationId, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (conversationId: string) => conversationApi.delete(conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  return {
    conversations: conversationsData?.conversations ?? [],
    isLoading,
    error: error as Error | null,
    createConversation: createMutation.mutateAsync,
    updateConversation: (conversationId: string, title: string) =>
      updateMutation.mutateAsync({ conversationId, title }),
    deleteConversation: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
}
