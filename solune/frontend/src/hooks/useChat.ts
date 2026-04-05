/**
 * Chat hook for managing messages and proposals.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { STALE_TIME_MEDIUM, TOAST_ERROR_MS } from '@/constants';
import { chatApi } from '@/services/api';
import type { ChatMessage, ProposalConfirmRequest } from '@/types';
import { useCommands } from '@/hooks/useCommands';
import { generateId } from '@/utils/generateId';
import { useChatProposals } from './useChatProposals';

const makeLocalMsg = (sender: 'user' | 'system', content: string): ChatMessage => ({
  message_id: generateId(),
  session_id: 'local',
  sender_type: sender,
  content,
  timestamp: new Date().toISOString(),
});

export function useChat() {
  const queryClient = useQueryClient();
  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingError, setStreamingError] = useState<string | null>(null);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const proposals = useChatProposals();

  const {
    data: messagesData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['chat', 'messages'],
    queryFn: chatApi.getMessages,
    staleTime: STALE_TIME_MEDIUM,
  });

  const clearChatMutation = useMutation({
    mutationFn: chatApi.clearMessages,
    onSuccess: () => {
      proposals.clearProposals();
      setLocalMessages([]);
      queryClient.invalidateQueries({ queryKey: ['chat', 'messages'] });
    },
  });

  const clearChat = useCallback(async () => {
    await clearChatMutation.mutateAsync();
  }, [clearChatMutation]);

  const allMessages = useMemo(
    () => [...(messagesData?.messages ?? []), ...localMessages],
    [messagesData, localMessages]
  );

  useEffect(() => {
    if (!streamingMessageId) return;
    const hasFinalMessage = (messagesData?.messages ?? []).some(
      (message) => message.message_id === streamingMessageId
    );
    if (hasFinalMessage) {
      const frame = requestAnimationFrame(() => {
        setStreamingContent('');
        setStreamingError(null);
        setStreamingMessageId(null);
      });
      return () => cancelAnimationFrame(frame);
    }
  }, [messagesData, streamingMessageId]);

  const { isCommand, executeCommand } = useCommands({ clearChat, messages: allMessages });

  const sendMutation = useMutation({
    mutationFn: chatApi.sendMessage,
    onSuccess: (response) => {
      proposals.handleActionResponse(response);
      queryClient.invalidateQueries({ queryKey: ['chat', 'messages'] });
    },
    onError: () => {
      toast.error('Failed to send message — check your connection and try again.', {
        duration: TOAST_ERROR_MS,
      });
    },
  });

  /** Streaming-aware send: uses SSE when ai_enhance is enabled, falls back to non-streaming. */
  const sendMessageStreaming = useCallback(
    (
      data: { content: string; ai_enhance?: boolean; file_urls?: string[]; pipeline_id?: string },
      tempId: string,
    ): Promise<void> => {
      const useStreaming = data.ai_enhance !== false;

      if (!useStreaming) {
        return sendMutation.mutateAsync(data).then(() => {
          setLocalMessages((prev) => prev.filter((m) => m.message_id !== tempId));
        });
      }

      return new Promise<void>((resolve) => {
        setIsStreaming(true);
        setStreamingContent('');
        setStreamingError(null);
        setStreamingMessageId(null);

        chatApi.sendMessageStream(
          data,
          (token) => {
            setStreamingContent((prev) => prev + token);
          },
          (response) => {
            setIsStreaming(false);
            setStreamingContent(response.content);
            setStreamingError(null);
            setStreamingMessageId(response.message_id);
            setLocalMessages((prev) => prev.filter((m) => m.message_id !== tempId));
            proposals.handleActionResponse(response);
            queryClient.invalidateQueries({ queryKey: ['chat', 'messages'] });
            resolve();
          },
          (error) => {
            setIsStreaming(false);
            setStreamingContent((prev) => error.partialContent ?? prev);
            setStreamingError(
              error.message || 'Failed to send message — check your connection and try again.'
            );
            setStreamingMessageId(null);
            setLocalMessages((prev) =>
              prev.map((m) =>
                m.message_id === tempId ? { ...m, status: 'failed' as const } : m,
              ),
            );
            toast.error(
              error.message || 'Failed to send message — check your connection and try again.',
              { duration: TOAST_ERROR_MS },
            );
            resolve();
          },
        );
      });
    },
    [sendMutation, proposals, queryClient],
  );

  const sendMessage = useCallback(
    async (
      content: string,
      options?: {
        isCommand?: boolean;
        aiEnhance?: boolean;
        fileUrls?: string[];
        pipelineId?: string;
      },
    ) => {
      const isCmd = options?.isCommand || isCommand(content);

      if (isCmd) {
        try {
          const result = await executeCommand(content);
          if (result.passthrough) {
            await sendMutation.mutateAsync({ content });
            return;
          }
          setLocalMessages((prev) => [
            ...prev,
            makeLocalMsg('user', content),
            makeLocalMsg('system', result.message),
          ]);
        } catch (error) {
          const msg =
            error instanceof Error ? `Command failed: ${error.message}` : 'Command failed.';
          setLocalMessages((prev) => [
            ...prev,
            makeLocalMsg('user', content),
            makeLocalMsg('system', msg),
          ]);
        }
        return;
      }

      const tempId = generateId();
      setLocalMessages((prev) => [
        ...prev,
        { ...makeLocalMsg('user', content), message_id: tempId, status: 'pending' as const },
      ]);

      try {
        await sendMessageStreaming(
          {
            content,
            ai_enhance: options?.aiEnhance ?? true,
            file_urls: options?.fileUrls ?? [],
            pipeline_id: options?.pipelineId,
          },
          tempId,
        );
      } catch {
        setLocalMessages((prev) =>
          prev.map((m) =>
            m.message_id === tempId ? { ...m, status: 'failed' as const } : m,
          ),
        );
      }
    },
    [sendMutation, sendMessageStreaming, isCommand, executeCommand],
  );

  const retryMessage = useCallback(
    async (messageId: string) => {
      const msg = localMessages.find(
        (m) => m.message_id === messageId && m.status === 'failed',
      );
      if (!msg) return;

      setLocalMessages((prev) =>
        prev.map((m) =>
          m.message_id === messageId ? { ...m, status: 'pending' as const } : m,
        ),
      );

      try {
        await sendMutation.mutateAsync({ content: msg.content });
        setLocalMessages((prev) => prev.filter((m) => m.message_id !== messageId));
      } catch {
        setLocalMessages((prev) =>
          prev.map((m) =>
            m.message_id === messageId ? { ...m, status: 'failed' as const } : m,
          ),
        );
      }
    },
    [localMessages, sendMutation],
  );

  const confirmProposal = useCallback(
    async (proposalId: string, edits?: ProposalConfirmRequest) => {
      try {
        await proposals.confirmProposal(proposalId, edits);
      } catch (error) {
        const msg =
          error instanceof Error
            ? `Task creation failed: ${error.message}`
            : 'Task creation failed.';
        setLocalMessages((prev) => [...prev, makeLocalMsg('system', msg)]);
      }
    },
    [proposals],
  );

  return {
    messages: allMessages,
    isLoading,
    isSending: sendMutation.isPending,
    isStreaming,
    streamingContent,
    streamingError,
    error: error as Error | null,
    pendingProposals: proposals.pendingProposals,
    pendingStatusChanges: proposals.pendingStatusChanges,
    pendingRecommendations: proposals.pendingRecommendations,
    sendMessage,
    retryMessage,
    confirmProposal,
    confirmStatusChange: proposals.confirmStatusChange,
    rejectProposal: proposals.rejectProposal,
    removePendingRecommendation: proposals.removePendingRecommendation,
    updateRecommendationStatus: proposals.updateRecommendationStatus,
    clearChat,
  };
}
