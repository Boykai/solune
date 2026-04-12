import type {
  ChatMessage,
  ChatMessageRequest,
  ChatMessagesResponse,
  AITaskProposal,
  ProposalConfirmRequest,
  FileUploadResponse,
  ThinkingEvent,
  Plan,
  PlanApprovalResponse,
  PlanExitResponse,
  PlanHistoryResponse,
  PlanStep,
  StepApprovalRequest,
  StepCreateRequest,
  StepFeedbackRequest,
  StepFeedbackResponse,
  StepReorderRequest,
  StepUpdateRequest,
  Conversation,
  ConversationsListResponse,
} from '@/types';
import { request, ApiError, API_BASE_URL, getCsrfToken } from './client';
import { ChatMessagesResponseSchema, ConversationsListResponseSchema } from '@/services/schemas/chat';
import { validateResponse } from '@/services/schemas/validate';

export const conversationApi = {
  /**
   * Create a new conversation.
   */
  create(title?: string): Promise<Conversation> {
    return request<Conversation>('/chat/conversations', {
      method: 'POST',
      body: JSON.stringify({ title: title ?? 'New Chat' }),
    });
  },

  /**
   * List conversations for the current session.
   */
  async list(): Promise<ConversationsListResponse> {
    const data = await request<ConversationsListResponse>('/chat/conversations');
    return validateResponse(ConversationsListResponseSchema, data, 'conversationApi.list');
  },

  /**
   * Update a conversation title.
   */
  update(conversationId: string, title: string): Promise<Conversation> {
    return request<Conversation>(`/chat/conversations/${conversationId}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    });
  },

  /**
   * Delete a conversation.
   */
  delete(conversationId: string): Promise<{ message: string }> {
    return request<{ message: string }>(`/chat/conversations/${conversationId}`, {
      method: 'DELETE',
    });
  },
};

export const chatApi = {
  /**
   * Get chat messages for current session.
   */
  async getMessages(conversationId?: string): Promise<ChatMessagesResponse> {
    const params = conversationId
      ? `?conversation_id=${encodeURIComponent(conversationId)}`
      : '';
    const data = await request<ChatMessagesResponse>(`/chat/messages${params}`);
    return validateResponse(ChatMessagesResponseSchema, data, 'chatApi.getMessages');
  },

  /**
   * Clear all chat messages for current session.
   */
  clearMessages(conversationId?: string): Promise<{ message: string }> {
    const params = conversationId
      ? `?conversation_id=${encodeURIComponent(conversationId)}`
      : '';
    return request<{ message: string }>(`/chat/messages${params}`, { method: 'DELETE' });
  },

  /**
   * Send a chat message.
   */
  sendMessage(data: ChatMessageRequest): Promise<ChatMessage> {
    return request<ChatMessage>('/chat/messages', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Send a chat message with streaming response via SSE.
   *
   * Yields progressive token events as they arrive from the agent.
   * Falls back to non-streaming sendMessage() on connection failure.
   *
   * @param data - The chat message request
   * @param onToken - Callback for each token chunk received
   * @param onDone - Callback when the complete message is ready
   * @param onError - Callback on error
   */
  async sendMessageStream(
    data: ChatMessageRequest,
    onToken: (content: string) => void,
    onDone: (message: ChatMessage) => void,
    onError: (error: Error & { partialContent?: string }) => void,
  ): Promise<void> {
    const url = `${API_BASE_URL}/chat/messages/stream`;
    const csrfToken = getCsrfToken();

    try {
      const response = await fetch(url, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
        },
        body: JSON.stringify(data),
      });

      if (!response.ok || !response.body) {
        // Fall back to non-streaming endpoint
        const fallbackResult = await chatApi.sendMessage(data);
        onDone(fallbackResult);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEventType = 'message';
      let currentDataLines: string[] = [];

      const tryParseJson = (value: unknown, fallback?: unknown): unknown => {
        if (typeof value !== 'string') return value ?? fallback;
        try { return JSON.parse(value); } catch { return fallback ?? value; }
      };

      const processFrame = (eventType: string, dataStr: string) => {
        const trimmedData = dataStr.trim();
        if (!trimmedData) return;

        let parsed: Record<string, unknown>;
        try {
          parsed = JSON.parse(trimmedData);
        } catch {
          console.debug('[SSE] Failed to parse event data:', trimmedData);
          return;
        }

        if (eventType === 'token') {
          const tokenData = tryParseJson(parsed.data, { content: parsed.data }) ?? parsed;
          const content = (tokenData as Record<string, unknown>).content;
          if (content) onToken(content as string);
        } else if (eventType === 'done') {
          const msgData = tryParseJson(parsed.data, parsed.data) ?? parsed;
          onDone(msgData as ChatMessage);
        } else if (eventType === 'error') {
          const errorData = tryParseJson(parsed.data, parsed) ?? parsed;
          let details: Record<string, unknown> = {};
          if (typeof errorData !== 'object' || errorData === null) {
            console.debug('[SSE] Unexpected error payload shape:', errorData);
          } else {
            details = errorData as Record<string, unknown>;
          }
          const error = new Error(
            (details.message || parsed.message || parsed.error || 'Stream error') as string
          ) as Error & { partialContent?: string };
          if (typeof details.partial_content === 'string') {
            error.partialContent = details.partial_content;
          }
          onError(error);
        } else if (parsed.content) {
          // Fallback: direct token content without explicit event type
          onToken(parsed.content as string);
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const rawLine of lines) {
          const line = rawLine.endsWith('\r') ? rawLine.slice(0, -1) : rawLine;

          if (line === '') {
            // Blank line = end of SSE frame
            if (currentDataLines.length > 0) {
              processFrame(currentEventType, currentDataLines.join('\n'));
              currentEventType = 'message';
              currentDataLines = [];
            }
            continue;
          }

          if (line.startsWith('event:')) {
            currentEventType = line.slice('event:'.length).trim();
          } else if (line.startsWith('data:')) {
            currentDataLines.push(line.slice('data:'.length).replace(/^ /, ''));
          }
        }
      }

      // Flush any remaining buffered frame when the stream ends
      if (currentDataLines.length > 0) {
        processFrame(currentEventType, currentDataLines.join('\n'));
      }
    } catch {
      // Fall back to non-streaming endpoint on any error
      try {
        const fallbackResult = await chatApi.sendMessage(data);
        onDone(fallbackResult);
      } catch (fallbackError) {
        onError(fallbackError instanceof Error ? fallbackError : new Error('Stream failed'));
      }
    }
  },

  /**
   * Confirm an AI task proposal.
   */
  confirmProposal(proposalId: string, data?: ProposalConfirmRequest): Promise<AITaskProposal> {
    return request<AITaskProposal>(`/chat/proposals/${proposalId}/confirm`, {
      method: 'POST',
      body: JSON.stringify(data || {}),
    });
  },

  /**
   * Cancel an AI task proposal.
   */
  cancelProposal(proposalId: string): Promise<void> {
    return request<void>(`/chat/proposals/${proposalId}`, {
      method: 'DELETE',
    });
  },

  /**
   * Upload a file for attachment to a future GitHub Issue.
   */
  async uploadFile(file: File): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const url = `${API_BASE_URL}/chat/upload`;
    const csrfToken = getCsrfToken();
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'include',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Upload failed' }));
      throw new ApiError(response.status, { error: errorData.error || 'Upload failed' });
    }

    return response.json();
  },

  /**
   * Send a plan-mode message (non-streaming).
   */
  sendPlanMessage(data: ChatMessageRequest): Promise<ChatMessage> {
    return request<ChatMessage>('/chat/messages/plan', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Enter plan mode with SSE streaming and thinking events.
   */
  async sendPlanMessageStream(
    data: ChatMessageRequest,
    onToken: (content: string) => void,
    onThinking: (event: ThinkingEvent) => void,
    onDone: (message: ChatMessage) => void,
    onError: (error: Error) => void,
  ): Promise<void> {
    const url = `${API_BASE_URL}/chat/messages/plan/stream`;
    const csrfToken = getCsrfToken();

    try {
      const response = await fetch(url, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
        },
        body: JSON.stringify(data),
      });

      if (!response.ok || !response.body) {
        // Fall back to non-streaming plan endpoint
        const fallbackResult = await chatApi.sendPlanMessage(data);
        onDone(fallbackResult);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEventType = 'message';
      let currentDataLines: string[] = [];

      const tryParseJson = (value: unknown, fallback?: unknown): unknown => {
        if (typeof value !== 'string') return value ?? fallback;
        try { return JSON.parse(value); } catch { return fallback ?? value; }
      };

      const processFrame = (eventType: string, dataStr: string) => {
        const trimmedData = dataStr.trim();
        if (!trimmedData) return;

        let parsed: Record<string, unknown>;
        try {
          parsed = JSON.parse(trimmedData);
        } catch {
          console.debug('[SSE] Failed to parse plan event data:', trimmedData);
          return;
        }

        if (eventType === 'thinking') {
          // parsed is validated by eventType; cast from generic JSON to typed event
          onThinking(parsed as unknown as ThinkingEvent);
        } else if (eventType === 'token') {
          let content: unknown;

          // Primary schema: backend sends { "content": "..." } as the event data.
          if (Object.prototype.hasOwnProperty.call(parsed, 'content')) {
            content = (parsed as { content?: unknown }).content;
          } else if (Object.prototype.hasOwnProperty.call(parsed, 'data')) {
            // Legacy/alternative schema: backend wraps content in a "data" field.
            const dataValue = (parsed as { data?: unknown }).data;
            const tokenData =
              tryParseJson(dataValue, { content: dataValue }) ?? parsed;
            content = (tokenData as Record<string, unknown>).content;
          }

          if (typeof content === 'string' && content) {
            onToken(content);
          }
        } else if (eventType === 'done') {
          const msgData = tryParseJson(parsed.data, parsed.data) ?? parsed;
          onDone(msgData as ChatMessage);
        } else if (eventType === 'error') {
          const message = (parsed.data || parsed.message || parsed.error || 'Stream error') as string;
          onError(new Error(message));
        } else if (parsed.content) {
          onToken(parsed.content as string);
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const rawLine of lines) {
          const line = rawLine.endsWith('\r') ? rawLine.slice(0, -1) : rawLine;

          if (line === '') {
            if (currentDataLines.length > 0) {
              processFrame(currentEventType, currentDataLines.join('\n'));
              currentEventType = 'message';
              currentDataLines = [];
            }
            continue;
          }

          if (line.startsWith('event:')) {
            currentEventType = line.slice('event:'.length).trim();
          } else if (line.startsWith('data:')) {
            currentDataLines.push(line.slice('data:'.length).replace(/^ /, ''));
          }
        }
      }

      if (currentDataLines.length > 0) {
        processFrame(currentEventType, currentDataLines.join('\n'));
      }
    } catch {
      // Fall back to non-streaming plan endpoint on any error
      try {
        const fallbackResult = await chatApi.sendPlanMessage(data);
        onDone(fallbackResult);
      } catch (fallbackError) {
        onError(fallbackError instanceof Error ? fallbackError : new Error('Plan stream failed'));
      }
    }
  },

  /**
   * Retrieve a plan by ID.
   */
  getPlan(planId: string): Promise<Plan> {
    return request<Plan>(`/chat/plans/${planId}`);
  },

  /**
   * Approve a plan and create GitHub issues.
   */
  approvePlan(planId: string): Promise<PlanApprovalResponse> {
    return request<PlanApprovalResponse>(`/chat/plans/${planId}/approve`, {
      method: 'POST',
    });
  },

  /**
   * Exit plan mode.
   */
  exitPlanMode(planId: string): Promise<PlanExitResponse> {
    return request<PlanExitResponse>(`/chat/plans/${planId}/exit`, {
      method: 'POST',
    });
  },

  // ============ Plan v2 API Methods ============

  /**
   * Get plan version history.
   */
  getPlanHistory(planId: string): Promise<PlanHistoryResponse> {
    return request<PlanHistoryResponse>(`/chat/plans/${planId}/history`);
  },

  /**
   * Add a new step to a plan.
   */
  addStep(planId: string, data: StepCreateRequest): Promise<PlanStep> {
    return request<PlanStep>(`/chat/plans/${planId}/steps`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update an existing plan step.
   */
  updateStep(planId: string, stepId: string, data: StepUpdateRequest): Promise<PlanStep> {
    return request<PlanStep>(`/chat/plans/${planId}/steps/${stepId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete a plan step.
   */
  deleteStep(planId: string, stepId: string): Promise<void> {
    return request<void>(`/chat/plans/${planId}/steps/${stepId}`, {
      method: 'DELETE',
    });
  },

  /**
   * Reorder plan steps.
   */
  reorderSteps(planId: string, data: StepReorderRequest): Promise<PlanStep[]> {
    return request<PlanStep[]>(`/chat/plans/${planId}/steps/reorder`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Approve or reject a single step.
   */
  approveStep(planId: string, stepId: string, data: StepApprovalRequest): Promise<PlanStep> {
    return request<PlanStep>(`/chat/plans/${planId}/steps/${stepId}/approve`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Submit step-level feedback.
   */
  submitStepFeedback(planId: string, stepId: string, data: StepFeedbackRequest): Promise<StepFeedbackResponse> {
    return request<StepFeedbackResponse>(`/chat/plans/${planId}/steps/${stepId}/feedback`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};
