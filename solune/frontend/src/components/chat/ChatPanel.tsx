/**
 * ChatPanel — Standalone chat panel wrapping ChatInterface for one conversation.
 *
 * Each panel owns its own useChat(conversationId) + usePlan() instances
 * so conversations are fully independent.
 */

import { useCallback, useState } from 'react';
import { X, Pencil, Check } from '@/lib/icons';
import { ChatInterface } from './ChatInterface';
import { useChat } from '@/hooks/useChat';
import { usePlan } from '@/hooks/usePlan';
import { useWorkflow } from '@/hooks/useWorkflow';
import { useConversations } from '@/hooks/useConversations';
import { useProjects } from '@/hooks/useProjects';
import { useAuth } from '@/hooks/useAuth';

interface ChatPanelProps {
  conversationId: string;
  title: string;
  onClose: () => void;
  showClose?: boolean;
}

export function ChatPanel({ conversationId, title, onClose, showClose = true }: ChatPanelProps) {
  const { user } = useAuth();
  const { selectedProject } = useProjects(user?.selected_project_id);
  const { updateConversation } = useConversations();

  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitle, setEditTitle] = useState(title);

  const {
    isPlanMode,
    setIsPlanMode,
    activePlan,
    setActivePlan,
    thinkingPhase,
    setThinkingPhase,
    thinkingDetail,
    setThinkingDetail,
    clearThinking,
    approveMutation,
    exitMutation,
  } = usePlan();

  const {
    messages,
    pendingProposals,
    pendingStatusChanges,
    pendingRecommendations,
    isSending,
    isStreaming,
    streamingContent,
    streamingError,
    sendMessage,
    retryMessage,
    confirmProposal,
    confirmStatusChange,
    rejectProposal,
    updateRecommendationStatus,
    clearChat,
  } = useChat({
    isPlanMode,
    onPlanThinking: (event) => {
      setThinkingPhase(event.phase);
      setThinkingDetail(event.detail ?? '');
    },
    clearPlanThinking: clearThinking,
    conversationId,
  });

  const { confirmRecommendation, rejectRecommendation } = useWorkflow();

  const approvePlanError = approveMutation.error
    ? approveMutation.error instanceof Error
      ? approveMutation.error.message
      : 'Failed to approve plan'
    : null;

  const handleSaveTitle = useCallback(async () => {
    const trimmed = editTitle.trim();
    if (trimmed && trimmed !== title) {
      try {
        await updateConversation(conversationId, trimmed);
      } catch {
        // Revert on failure
        setEditTitle(title);
      }
    } else {
      setEditTitle(title);
    }
    setIsEditingTitle(false);
  }, [editTitle, title, conversationId, updateConversation]);

  return (
    <div className="flex h-full flex-col" data-testid="chat-panel">
      {/* Panel header */}
      <div className="flex items-center gap-2 border-b border-border/50 px-3 py-2">
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          {isEditingTitle ? (
            <div className="flex items-center gap-1">
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveTitle();
                  if (e.key === 'Escape') {
                    setEditTitle(title);
                    setIsEditingTitle(false);
                  }
                }}
                onBlur={handleSaveTitle}
                className="h-6 rounded border border-border bg-background px-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                autoFocus
                maxLength={200}
                aria-label="Edit conversation title"
              />
              <button
                type="button"
                onClick={handleSaveTitle}
                className="rounded p-0.5 text-muted-foreground hover:text-foreground"
                aria-label="Save title"
              >
                <Check className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => {
                setEditTitle(title);
                setIsEditingTitle(true);
              }}
              className="group flex min-w-0 items-center gap-1 truncate text-sm font-medium text-foreground"
              title={title}
              aria-label="Edit conversation title"
            >
              <span className="truncate">{title}</span>
              <Pencil className="h-3 w-3 shrink-0 opacity-0 transition-opacity group-hover:opacity-70" />
            </button>
          )}
        </div>
        {showClose && (
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
            aria-label="Close chat panel"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Chat interface */}
      <div className="flex-1 overflow-hidden">
        <ChatInterface
          messages={messages}
          pendingProposals={pendingProposals}
          pendingStatusChanges={pendingStatusChanges}
          pendingRecommendations={pendingRecommendations}
          isSending={isSending}
          isStreaming={isStreaming}
          streamingContent={streamingContent}
          streamingError={streamingError}
          projectId={selectedProject?.project_id}
          onSendMessage={sendMessage}
          onRetryMessage={retryMessage}
          onConfirmProposal={async (proposalId) => {
            await confirmProposal(proposalId);
          }}
          onConfirmStatusChange={confirmStatusChange}
          onConfirmRecommendation={async (recommendationId) => {
            const result = await confirmRecommendation(recommendationId);
            if (result.success) {
              updateRecommendationStatus(recommendationId, 'confirmed');
            }
            return result;
          }}
          onRejectProposal={rejectProposal}
          onRejectRecommendation={async (recommendationId) => {
            await rejectRecommendation(recommendationId);
            updateRecommendationStatus(recommendationId, 'rejected');
          }}
          onNewChat={async () => {
            setActivePlan(null);
            setIsPlanMode(false);
            clearThinking();
            await clearChat();
          }}
          thinkingPhase={thinkingPhase}
          thinkingDetail={thinkingDetail}
          isPlanMode={isPlanMode}
          planProjectName={activePlan?.project_name}
          onApprovePlan={(planId) => approveMutation.mutateAsync(planId)}
          onExitPlanMode={async (planId) => {
            await exitMutation.mutateAsync(planId);
          }}
          approvedPlanData={approveMutation.data ?? null}
          isApprovingPlan={approveMutation.isPending}
          approvePlanError={approvePlanError}
        />
      </div>
    </div>
  );
}
