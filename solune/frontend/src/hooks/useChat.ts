/**
 * Chat hook for managing messages and proposals.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { STALE_TIME_MEDIUM, TOAST_ERROR_MS } from '@/constants';
import { chatApi } from '@/services/api';
import type { ChatMessage, ProposalConfirmRequest, ThinkingEvent } from '@/types';
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

const isPlanCommand = (content: string) => content.trimStart().toLowerCase().startsWith('/plan');

interface UseChatOptions {
  isPlanMode?: boolean;
  onPlanThinking?: (event: ThinkingEvent) => void;
  clearPlanThinking?: () => void;
  conversationId?: string;
}

export function useChat({
  isPlanMode = false,
  onPlanThinking,
  clearPlanThinking,
  conversationId,
}: UseChatOptions = {}) {
  const queryClient = useQueryClient();
  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingError, setStreamingError] = useState<string | null>(null);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const proposals = useChatProposals();

  const queryKey = useMemo(() => ['chat', 'messages', conversationId ?? 'global'], [conversationId]);

  const {
    data: messagesData,
    isLoading,
    error,
  } = useQuery({
    queryKey,
    queryFn: () => chatApi.getMessages(conversationId),
    staleTime: STALE_TIME_MEDIUM,
  });

  const clearChatMutation = useMutation({
    mutationFn: () => chatApi.clearMessages(conversationId),
    onSuccess: () => {
      proposals.clearProposals();
      setLocalMessages([]);
      queryClient.invalidateQueries({ queryKey });
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
      // Defer cleanup to the next frame so the final persisted message can paint
      // before the transient streaming bubble is removed.
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
    mutationFn: (data: Parameters<typeof chatApi.sendMessage>[0]) =>
      chatApi.sendMessage(conversationId ? { ...data, conversation_id: conversationId } : data),
    onSuccess: (response) => {
      proposals.handleActionResponse(response);
      queryClient.invalidateQueries({ queryKey });
    },
    onError: () => {
      toast.error('Failed to send message — check your connection and try again.', {
        duration: TOAST_ERROR_MS,
      });
    },
  });

  const clearStreamingPreview = useCallback(() => {
    setStreamingContent('');
    setStreamingError(null);
    setStreamingMessageId(null);
  }, []);

  const shouldUsePlanTransport = useCallback(
    (content: string, isCommandInput = false) => {
      if (isPlanCommand(content)) {
        return true;
      }

      return isPlanMode && !isCommandInput;
    },
    [isPlanMode],
  );

  const handleTransportSuccess = useCallback(
    (response: ChatMessage, tempId: string, suppressPreview = false) => {
      setIsStreaming(false);

      if (suppressPreview) {
        clearStreamingPreview();
      } else {
        setStreamingContent(response.content);
        setStreamingError(null);
        setStreamingMessageId(response.message_id);
      }

      clearPlanThinking?.();
      setLocalMessages((prev) => prev.filter((m) => m.message_id !== tempId));
      proposals.handleActionResponse(response);
      queryClient.invalidateQueries({ queryKey });
    },
    [clearPlanThinking, clearStreamingPreview, proposals, queryClient, queryKey],
  );

  const handleTransportFailure = useCallback(
    (
      tempId: string,
      errorMessage: string,
      partialContent?: string,
      suppressPreview = false,
    ) => {
      setIsStreaming(false);

      if (suppressPreview) {
        clearStreamingPreview();
      } else {
        setStreamingContent((prev) => partialContent ?? prev);
        setStreamingError(errorMessage);
        setStreamingMessageId(null);
      }

      clearPlanThinking?.();
      setLocalMessages((prev) =>
        prev.map((m) =>
          m.message_id === tempId ? { ...m, status: 'failed' as const } : m,
        ),
      );
      toast.error(errorMessage, { duration: TOAST_ERROR_MS });
    },
    [clearPlanThinking, clearStreamingPreview],
  );

  /** Streaming-aware send: uses SSE when ai_enhance is enabled, falls back to non-streaming. */
  const sendMessageStreaming = useCallback(
    (
      data: { content: string; ai_enhance?: boolean; file_urls?: string[]; pipeline_id?: string },
      tempId: string,
      options?: { isCommandInput?: boolean },
    ): Promise<void> => {
      const useStreaming = data.ai_enhance !== false;
      const usePlanTransport = shouldUsePlanTransport(
        data.content,
        options?.isCommandInput ?? false,
      );

      // Inject conversation_id into request data when scoped to a conversation
      const requestData = conversationId ? { ...data, conversation_id: conversationId } : data;

      if (!useStreaming) {
        if (usePlanTransport) {
          clearPlanThinking?.();

          return chatApi
            .sendPlanMessage(requestData)
            .then((response) => {
              handleTransportSuccess(response, tempId, response.action_type === 'plan_create');
            })
            .catch((error) => {
              const message =
                error instanceof Error
                  ? error.message
                  : 'Failed to send message — check your connection and try again.';
              handleTransportFailure(tempId, message, undefined, true);
            });
        }

        return sendMutation.mutateAsync(requestData).then(() => {
          setLocalMessages((prev) => prev.filter((m) => m.message_id !== tempId));
        });
      }

      return new Promise<void>((resolve) => {
        setIsStreaming(true);
        clearStreamingPreview();

        if (usePlanTransport) {
          clearPlanThinking?.();

          chatApi.sendPlanMessageStream(
            requestData,
            () => {
              // Suppress raw plan-mode token prose. The dedicated thinking events
              // drive the visible plan progress indicator instead.
            },
            (event) => {
              onPlanThinking?.(event);
            },
            (response) => {
              handleTransportSuccess(response, tempId, response.action_type === 'plan_create');
              resolve();
            },
            (error) => {
              const message =
                error.message || 'Failed to send message — check your connection and try again.';
              handleTransportFailure(tempId, message, undefined, true);
              resolve();
            },
          );
          return;
        }

        chatApi.sendMessageStream(
          requestData,
          (token) => {
            setStreamingContent((prev) => prev + token);
          },
          (response) => {
            handleTransportSuccess(response, tempId);
            resolve();
          },
          (error) => {
            handleTransportFailure(
              tempId,
              error.message || 'Failed to send message — check your connection and try again.',
              error.partialContent,
            );
            resolve();
          },
        );
      });
    },
    [
      clearPlanThinking,
      clearStreamingPreview,
      conversationId,
      handleTransportFailure,
      handleTransportSuccess,
      onPlanThinking,
      sendMutation,
      shouldUsePlanTransport,
    ],
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
      const isPlanRequest = isPlanCommand(content);
      const isCmd = !isPlanRequest && (options?.isCommand || isCommand(content));

      if (isCmd) {
        try {
          const result = await executeCommand(content);
          if (result.passthrough) {
            await sendMessageStreaming({ content }, generateId(), { isCommandInput: true });
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
    [sendMessageStreaming, isCommand, executeCommand],
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
        await sendMessageStreaming({ content: msg.content }, messageId);
      } catch {
        setLocalMessages((prev) =>
          prev.map((m) =>
            m.message_id === messageId ? { ...m, status: 'failed' as const } : m,
          ),
        );
      }
    },
    [localMessages, sendMessageStreaming],
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
