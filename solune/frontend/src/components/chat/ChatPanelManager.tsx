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

export function ChatPanelManager() {
  const { conversations, createConversation, deleteConversation } = useConversations();
  const [isInitialized, setIsInitialized] = useState(false);
  const [initialConvId, setInitialConvId] = useState<string | undefined>(undefined);

  const {
    panels,
    addPanel,
    removePanel,
    resizePanels,
    containerRef,
  } = useChatPanels(initialConvId);

  const isMobile = useMediaQuery('(max-width: 767px)');
  const [activeTabIndex, setActiveTabIndex] = useState(0);

  // Create a default conversation on first mount if there are no panels
  useEffect(() => {
    if (isInitialized) return;

    const init = async () => {
      if (panels.length === 0) {
        try {
          const conv = await createConversation('New Chat');
          setInitialConvId(conv.conversation_id);
        } catch {
          // fallback — will show empty state
        }
      }
      setIsInitialized(true);
    };
    init();
  }, [isInitialized, panels.length, createConversation]);

  const handleAddPanel = useCallback(async () => {
    try {
      const conv = await createConversation('New Chat');
      addPanel(conv.conversation_id);
    } catch {
      // Failed to create conversation
    }
  }, [createConversation, addPanel]);

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
          const minPct = (MIN_WIDTH_PX / resizeState.current.containerWidth) * 100;
          if (newLeft < minPct) {
            newLeft = minPct;
            newRight = resizeState.current.leftStartPct + resizeState.current.rightStartPct - minPct;
          }
          if (newRight < minPct) {
            newRight = minPct;
            newLeft = resizeState.current.leftStartPct + resizeState.current.rightStartPct - minPct;
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

  if (panels.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <div className="text-center">
          <p className="mb-2 text-lg">Starting your chat...</p>
        </div>
      </div>
    );
  }

  // Mobile: tab-based view
  if (isMobile) {
    return (
      <div className="flex h-full flex-col" data-testid="chat-panel-manager">
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
              className="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
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
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
              aria-label="Add new chat"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Chat
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
      className="flex h-full"
      data-testid="chat-panel-manager"
    >
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
          className="mx-1 rounded-md p-2 text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
          aria-label="Add new chat"
          title="Add new chat panel"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
