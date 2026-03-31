/**
 * useBuildProgress — WebSocket subscription for build progress events.
 * Filters events by app_name and exposes current progress state.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  BuildCompletePayload,
  BuildFailedPayload,
  BuildMilestonePayload,
  BuildProgressPayload,
} from '@/types/app-template';

type BuildEvent = BuildProgressPayload | BuildMilestonePayload | BuildCompletePayload | BuildFailedPayload;

interface UseBuildProgressReturn {
  progress: BuildProgressPayload | null;
  milestones: BuildMilestonePayload[];
  completion: BuildCompletePayload | null;
  failure: BuildFailedPayload | null;
  isActive: boolean;
}

/**
 * Subscribe to build progress events for a specific app via existing WebSocket.
 *
 * @param appName - App name to filter events for.
 * @param wsRef - Reference to the existing WebSocket connection.
 */
export function useBuildProgress(
  appName: string | null,
  wsRef?: React.RefObject<WebSocket | null>,
): UseBuildProgressReturn {
  const [progress, setProgress] = useState<BuildProgressPayload | null>(null);
  const [milestones, setMilestones] = useState<BuildMilestonePayload[]>([]);
  const [completion, setCompletion] = useState<BuildCompletePayload | null>(null);
  const [failure, setFailure] = useState<BuildFailedPayload | null>(null);

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as BuildEvent;
        if (!appName || !('app_name' in data) || data.app_name !== appName) {
          return;
        }

        switch (data.type) {
          case 'build_progress':
            setProgress(data as BuildProgressPayload);
            break;
          case 'build_milestone':
            setMilestones((prev) => [...prev, data as BuildMilestonePayload]);
            break;
          case 'build_complete':
            setCompletion(data as BuildCompletePayload);
            break;
          case 'build_failed':
            setFailure(data as BuildFailedPayload);
            break;
        }
      } catch {
        // Ignore non-JSON or unrelated messages
      }
    },
    [appName],
  );

  useEffect(() => {
    const ws = wsRef?.current;
    if (!ws || !appName) return;

    ws.addEventListener('message', handleMessage);
    return () => {
      ws.removeEventListener('message', handleMessage);
    };
  }, [wsRef, appName, handleMessage]);

  const isActive = progress !== null && progress.phase !== 'complete' && progress.phase !== 'failed';

  return { progress, milestones, completion, failure, isActive };
}
