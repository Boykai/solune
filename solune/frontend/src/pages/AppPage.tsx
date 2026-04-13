/**
 * AppPage — primary multi-chat experience with side-by-side resizable panels.
 */

import { ChatPanelManager } from '@/components/chat/ChatPanelManager';

export function AppPage() {
  return (
    <div className="h-full min-h-0 w-full overflow-hidden">
      <ChatPanelManager />
    </div>
  );
}
