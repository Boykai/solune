/**
 * AppPage — primary multi-chat experience with side-by-side resizable panels.
 */

import { ChatPanelManager } from '@/components/chat/ChatPanelManager';

export function AppPage() {
  return (
    <div className="h-[calc(100vh-3.5rem)] w-full overflow-hidden">
      <ChatPanelManager />
    </div>
  );
}
