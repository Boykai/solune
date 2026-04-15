/**
 * ChatPanelManager — Multi-panel container for the AppPage.
 *
 * Renders ChatPanel components side-by-side with draggable resize handles.
 * On mobile (< 768px), displays panels one-at-a-time with tab switching.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Plus } from '@/lib/icons';
import { ChatPanel } from './ChatPanel';
import { useChatPanels } from '@/hooks/useChatPanels';
import { useConversations } from '@/hooks/useConversations';
import { useMediaQuery } from '@/hooks/useMediaQuery';

const MIN_WIDTH_PX = 320;

function getBootstrapErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallback;
}

function buildKnownConversationIds(
  conversations: Array<{ conversation_id: string }>,
  provisionalConversationId?: string,
): Set<string> {
  const validIds = new Set(conversations.map((conversation) => conversation.conversation_id));
  if (provisionalConversationId) {
    validIds.add(provisionalConversationId);
  }
  return validIds;
}

export function ChatPanelManager() {
  const {
    conversations,
    isLoading: isConversationsLoading,
    isFetching: isConversationsFetching,
    error: conversationsError,
    createConversation,
    deleteConversation,
    refetch: refetchConversations,
  } = useConversations();
  const [provisionalConversationId, setProvisionalConversationId] = useState<string | undefined>(undefined);
  const [bootstrapError, setBootstrapError] = useState<string | null>(null);
  const bootstrapRunIdRef = useRef(0);
  const seededConversationId = provisionalConversationId ?? conversations[0]?.conversation_id;

  const {
    panels,
    addPanel,
    removePanel,
    resizePanels,
    removeStalePanels,
    containerRef,
  } = useChatPanels(seededConversationId);

  const isMobile = useMediaQuery('(max-width: 767px)');
  const [activeTabIndex, setActiveTabIndex] = useState(0);

  // Reconcile panels against loaded conversations to drop stale entries
  useEffect(() => {
    if (isConversationsLoading || isConversationsFetching || conversationsError || panels.length === 0) return;

    const validIds = buildKnownConversationIds(conversations, provisionalConversationId);
    const hasStalePanels = panels.some((panel) => !validIds.has(panel.conversationId));

    if (!hasStalePanels) return;

    removeStalePanels(validIds);
  }, [
    conversations,
    conversationsError,
    provisionalConversationId,
    isConversationsFetching,
    isConversationsLoading,
    panels,
    removeStalePanels,
  ]);

  // Bootstrap the first visible panel from an existing conversation or create one when the
  // current session is genuinely empty. Failures surface a retry UI instead of an endless
  // loading placeholder.
  useEffect(() => {
    if (isConversationsLoading || conversationsError || bootstrapError) return;

    const validIds = buildKnownConversationIds(conversations, provisionalConversationId);
    const hasStalePanels = panels.some((panel) => !validIds.has(panel.conversationId));
    if (hasStalePanels) {
      return;
    }

    if (panels.length > 0 || seededConversationId) {
      return;
    }

    const currentRunId = bootstrapRunIdRef.current + 1;
    bootstrapRunIdRef.current = currentRunId;

    let cancelled = false;

    void createConversation('New Chat')
      .then((conversation) => {
        if (cancelled || bootstrapRunIdRef.current !== currentRunId) return;
        setProvisionalConversationId(conversation.conversation_id);
      })
      .catch((error) => {
        if (cancelled || bootstrapRunIdRef.current !== currentRunId) return;
        setBootstrapError(getBootstrapErrorMessage(error, "Couldn't start your chat."));
      });

    return () => {
      cancelled = true;
    };
  }, [
    bootstrapError,
    conversations,
    conversationsError,
    createConversation,
    isConversationsLoading,
    panels,
    provisionalConversationId,
    seededConversationId,
  ]);

  const handleRetryBootstrap = useCallback(() => {
    bootstrapRunIdRef.current += 1;
    setBootstrapError(null);
    setProvisionalConversationId(undefined);
    void refetchConversations();
  }, [refetchConversations]);

  const [isAddingPanel, setIsAddingPanel] = useState(false);
  const [addPanelError, setAddPanelError] = useState<string | null>(null);

  const handleAddPanel = useCallback(async () => {
    if (isAddingPanel) return;
    setIsAddingPanel(true);
    setAddPanelError(null);
    try {
      const conv = await createConversation('New Chat');
      addPanel(conv.conversation_id);
    } catch (err) {
      const message = err instanceof Error && err.message.trim() ? err.message : 'Could not create a new chat.';
      setAddPanelError(message);
    } finally {
      setIsAddingPanel(false);
    }
  }, [isAddingPanel, createConversation, addPanel]);

  const handleRemovePanel = useCallback(
    async (panelId: string, conversationId: string) => {
      removePanel(panelId);
      try {
        await deleteConversation(conversationId);
      } catch {
        // Non-critical — conversation cleanup can fail
      }
    },
    [removePanel, deleteConversation],
  );

  // Resize drag state
  const resizeState = useRef<{
    leftId: string;
    rightId: string;
    startX: number;
    leftStartPct: number;
    rightStartPct: number;
    containerWidth: number;
  } | null>(null);

  const onResizeStart = useCallback(
    (e: React.MouseEvent | React.TouchEvent, leftIdx: number) => {
      e.preventDefault();
      const container = containerRef.current;
      if (!container) return;

      const leftPanel = panels[leftIdx];
      const rightPanel = panels[leftIdx + 1];
      if (!leftPanel || !rightPanel) return;

      const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
      const containerWidth = container.offsetWidth;

      resizeState.current = {
        leftId: leftPanel.panelId,
        rightId: rightPanel.panelId,
        startX: clientX,
        leftStartPct: leftPanel.widthPercent,
        rightStartPct: rightPanel.widthPercent,
        containerWidth,
      };

      let rafId = 0;
      const onMove = (ev: MouseEvent | TouchEvent) => {
        if (!resizeState.current) return;
        if (rafId) return;
        rafId = requestAnimationFrame(() => {
          rafId = 0;
          if (!resizeState.current) return;
          const cx = 'touches' in ev ? ev.touches[0].clientX : ev.clientX;
          const dx = cx - resizeState.current.startX;
          const deltaPct = (dx / resizeState.current.containerWidth) * 100;

          let newLeft = resizeState.current.leftStartPct + deltaPct;
          let newRight = resizeState.current.rightStartPct - deltaPct;

          // Enforce min-width as a percentage
          const totalPct = resizeState.current.leftStartPct + resizeState.current.rightStartPct;
          const minPct = (MIN_WIDTH_PX / resizeState.current.containerWidth) * 100;

          // If the container is too narrow for both panels to meet min-width, bail out
          if (minPct * 2 > totalPct) return;

          if (newLeft < minPct) {
            newLeft = minPct;
            newRight = totalPct - minPct;
          }
          if (newRight < minPct) {
            newRight = minPct;
            newLeft = totalPct - minPct;
          }

          resizePanels(
            resizeState.current.leftId,
            resizeState.current.rightId,
            newLeft,
            newRight,
          );
        });
      };

      const onEnd = () => {
        resizeState.current = null;
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onEnd);
        window.removeEventListener('touchmove', onMove);
        window.removeEventListener('touchend', onEnd);
        if (rafId) cancelAnimationFrame(rafId);
      };

      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onEnd);
      window.addEventListener('touchmove', onMove, { passive: false });
      window.addEventListener('touchend', onEnd);
    },
    [panels, containerRef, resizePanels],
  );

  // Get title for a panel from conversations
  const getTitle = useCallback(
    (conversationId: string) => {
      const conv = conversations.find((c) => c.conversation_id === conversationId);
      return conv?.title ?? 'New Chat';
    },
    [conversations],
  );

  // Ensure active tab is valid — computed rather than set in effect
  const safeActiveTab = activeTabIndex >= panels.length && panels.length > 0
    ? panels.length - 1
    : activeTabIndex;

  const bootstrapFailureMessage = bootstrapError
    ?? (panels.length === 0 && !seededConversationId && conversationsError
      ? getBootstrapErrorMessage(conversationsError, 'Could not load chat conversations.')
      : null);

  const isBootstrapping =
    !isConversationsLoading
    && !bootstrapFailureMessage
    && panels.length === 0
    && !seededConversationId;

  if (panels.length === 0) {
    if (bootstrapFailureMessage) {
      return (
        <div className="flex h-full items-center justify-center px-6 py-10" data-testid="chat-bootstrap-error">
          <div
            role="alert"
            className="celestial-panel w-full max-w-md rounded-[1.5rem] border border-border/80 px-6 py-5 text-center shadow-lg"
          >
            <p className="text-lg font-medium text-foreground">Could not start your chat</p>
            <p className="mt-2 text-sm text-muted-foreground">{bootstrapFailureMessage}</p>
            <button
              type="button"
              onClick={handleRetryBootstrap}
              className="mt-4 inline-flex items-center justify-center rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <div className="text-center">
          <p className="mb-2 text-lg">
            {conversations.length > 0 || seededConversationId ? 'Opening your chat...' : 'Starting your chat...'}
          </p>
          {isBootstrapping && <p className="text-sm text-muted-foreground/80">Creating a conversation for this session.</p>}
        </div>
      </div>
    );
  }

  // Mobile: tab-based view
  if (isMobile) {
    return (
      <div className="flex h-full flex-col" data-testid="chat-panel-manager">
        {addPanelError && (
          <div role="alert" className="mx-2 mt-1 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-1.5 text-xs text-destructive">
            {addPanelError}
          </div>
        )}
        {/* Tab bar */}
        {panels.length > 1 && (
          <div className="flex items-center gap-1 overflow-x-auto border-b border-border/50 px-2 py-1">
            {panels.map((panel, idx) => (
              <button
                key={panel.panelId}
                type="button"
                onClick={() => setActiveTabIndex(idx)}
                className={`shrink-0 truncate rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  idx === safeActiveTab
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-muted/50'
                }`}
                style={{ maxWidth: '120px' }}
              >
                {getTitle(panel.conversationId).substring(0, 15)}
              </button>
            ))}
            <button
              type="button"
              onClick={handleAddPanel}
              disabled={isAddingPanel}
              className="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary disabled:pointer-events-none disabled:opacity-50"
              aria-label="Add new chat"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {/* Active panel */}
        <div className="flex-1 overflow-hidden">
          {panels.map((panel, idx) => (
            <div
              key={panel.panelId}
              className={idx === safeActiveTab ? 'h-full' : 'hidden'}
            >
              <ChatPanel
                conversationId={panel.conversationId}
                title={getTitle(panel.conversationId)}
                onClose={() => handleRemovePanel(panel.panelId, panel.conversationId)}
                showClose={panels.length > 1}
              />
            </div>
          ))}
        </div>

        {/* Add button when only one panel (no tab bar shown) */}
        {panels.length === 1 && (
          <div className="flex justify-center border-t border-border/50 py-1">
            <button
              type="button"
              onClick={handleAddPanel}
              disabled={isAddingPanel}
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary disabled:pointer-events-none disabled:opacity-50"
              aria-label="Add new chat"
            >
              <Plus className="h-3.5 w-3.5" />
              {isAddingPanel ? 'Adding…' : 'Add Chat'}
            </button>
          </div>
        )}
      </div>
    );
  }

  // Desktop: side-by-side layout
  return (
    <div
      ref={containerRef}
      className="flex h-full flex-col"
      data-testid="chat-panel-manager"
    >
      {addPanelError && (
        <div role="alert" className="mx-2 mt-1 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-1.5 text-xs text-destructive">
          {addPanelError}
        </div>
      )}
      <div className="flex flex-1 min-h-0">
      {panels.map((panel, idx) => (
        <div key={panel.panelId} className="flex h-full" style={{ width: `${panel.widthPercent}%` }}>
          {/* Resize handle (between panels) */}
          {idx > 0 && (
            <button
              type="button"
              className="flex w-1.5 shrink-0 cursor-col-resize items-center justify-center bg-border/30 transition-colors hover:bg-primary/20"
              onMouseDown={(e) => onResizeStart(e, idx - 1)}
              onTouchStart={(e) => onResizeStart(e, idx - 1)}
              aria-label="Resize panels"
            >
              <div className="h-8 w-0.5 rounded-full bg-muted-foreground/30" />
            </button>
          )}
          <div className="flex-1 overflow-hidden border-r border-border/30 last:border-r-0">
            <ChatPanel
              conversationId={panel.conversationId}
              title={getTitle(panel.conversationId)}
              onClose={() => handleRemovePanel(panel.panelId, panel.conversationId)}
              showClose={panels.length > 1}
            />
          </div>
        </div>
      ))}

      {/* Add chat button */}
      <div className="flex shrink-0 items-start border-l border-border/30 pt-2">
        <button
          type="button"
          onClick={handleAddPanel}
          disabled={isAddingPanel}
          className="mx-1 rounded-md p-2 text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary disabled:pointer-events-none disabled:opacity-50"
          aria-label="Add new chat"
          title="Add new chat panel"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      </div>
    </div>
  );
}
