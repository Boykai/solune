/**
 * ChatToolbar — persistent toolbar above the chat input containing the
 * file upload button and microphone button.
 * Styled consistently with the AddAgentPopover pattern.
 */

import { useRef } from 'react';
import { Paperclip } from '@/lib/icons';
import { VoiceInputButton } from './VoiceInputButton';
import { Tooltip } from '@/components/ui/tooltip';

interface ChatToolbarProps {
  onFileSelect: (files: FileList) => void;
  isRecording: boolean;
  isVoiceSupported: boolean;
  onVoiceToggle: () => void;
  voiceError: string | null;
  fileCount: number;
}

export function ChatToolbar({
  onFileSelect,
  isRecording,
  isVoiceSupported,
  onVoiceToggle,
  voiceError,
  fileCount,
}: ChatToolbarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileSelect(e.target.files);
      // Reset so the same file can be selected again
      e.target.value = '';
    }
  };

  return (
    <div className="flex items-center justify-end border-b border-border bg-background/62 px-4 py-2">
      {/* Action buttons */}
      <div className="flex items-center gap-1">
        {/* File upload button */}
        <Tooltip contentKey="chat.toolbar.attachButton">
          <button
            type="button"
            onClick={handleFileClick}
            className="celestial-focus relative flex h-11 w-11 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-primary/10 hover:text-foreground focus-visible:outline-none md:h-8 md:w-8"
            aria-label="Attach file"
          >
            <Paperclip className="w-4 h-4" />
            {fileCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-4 h-4 flex items-center justify-center text-[10px] font-bold rounded-full bg-primary text-primary-foreground">
                {fileCount}
              </span>
            )}
          </button>
        </Tooltip>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/png,image/jpeg,image/gif,image/webp,image/svg+xml,application/pdf,text/plain,text/markdown,text/csv,application/json,application/x-yaml,application/zip,.vtt,.srt"
          onChange={handleFileChange}
          className="hidden"
          aria-hidden="true"
        />

        {/* Voice input button */}
        <Tooltip
          content={
            !isVoiceSupported
              ? 'Voice input is not supported in this browser.'
              : isRecording
                ? 'Click to stop recording.'
                : voiceError
                  ? voiceError
                  : undefined
          }
          contentKey={
            isVoiceSupported && !isRecording && !voiceError
              ? 'chat.toolbar.voiceButton'
              : undefined
          }
        >
          <span className="inline-flex">
            <VoiceInputButton
              isSupported={isVoiceSupported}
              isRecording={isRecording}
              onToggle={onVoiceToggle}
              error={voiceError}
            />
          </span>
        </Tooltip>
      </div>
    </div>
  );
}
