import { describe, expect, it, vi } from 'vitest';
import { fireEvent } from '@testing-library/react';
import { render, screen } from '@/test/test-utils';
import { ChatToolbar } from './ChatToolbar';

// ── Mocks ──

vi.mock('./VoiceInputButton', () => ({
  VoiceInputButton: ({
    isSupported,
    isRecording,
    onToggle,
    error,
  }: {
    isSupported: boolean;
    isRecording: boolean;
    onToggle: () => void;
    error: string | null;
  }) => (
    <button
      data-testid="voice-btn"
      onClick={onToggle}
      disabled={!isSupported}
      aria-label={isRecording ? 'Stop recording' : 'Start recording'}
    >
      {isRecording ? 'Recording' : 'Voice'}
      {error && <span data-testid="voice-error">{error}</span>}
    </button>
  ),
}));

// ── Tests ──

describe('ChatToolbar', () => {
  const defaultProps = {
    onFileSelect: vi.fn(),
    isRecording: false,
    isVoiceSupported: true,
    onVoiceToggle: vi.fn(),
    voiceError: null,
    fileCount: 0,
  };

  it('renders the attach file button', () => {
    render(<ChatToolbar {...defaultProps} />);
    expect(screen.getByLabelText('Attach file')).toBeInTheDocument();
  });

  it('renders the voice input button', () => {
    render(<ChatToolbar {...defaultProps} />);
    expect(screen.getByTestId('voice-btn')).toBeInTheDocument();
  });

  it('shows file count badge when files are attached', () => {
    render(<ChatToolbar {...defaultProps} fileCount={3} />);
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('hides file count badge when fileCount is 0', () => {
    const { container } = render(<ChatToolbar {...defaultProps} fileCount={0} />);
    // Badge should not be present — the file count span has specific styling
    expect(container.querySelector('.bg-primary.text-primary-foreground')).toBeNull();
  });

  it('calls onFileSelect when files are selected via input', () => {
    const onFileSelect = vi.fn();
    render(<ChatToolbar {...defaultProps} onFileSelect={onFileSelect} />);
    
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).not.toBeNull();
    
    const file = new File(['hello'], 'test.txt', { type: 'text/plain' });
    const dt = new DataTransfer();
    dt.items.add(file);
    
    // Assign via the DataTransfer API (happy-dom supports it)
    Object.defineProperty(fileInput, 'files', {
      value: dt.files,
      writable: true,
      configurable: true,
    });
    
    fireEvent.change(fileInput);
    expect(onFileSelect).toHaveBeenCalledOnce();
  });

  it('accepts the expected file types', () => {
    render(<ChatToolbar {...defaultProps} />);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput.accept).toContain('image/png');
    expect(fileInput.accept).toContain('application/pdf');
    expect(fileInput.accept).toContain('application/json');
  });

  it('allows multiple file selection', () => {
    render(<ChatToolbar {...defaultProps} />);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput.multiple).toBe(true);
  });

  it('hides the file input visually', () => {
    render(<ChatToolbar {...defaultProps} />);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput.className).toContain('hidden');
  });

  it('calls onVoiceToggle when voice button is clicked', () => {
    const onVoiceToggle = vi.fn();
    render(<ChatToolbar {...defaultProps} onVoiceToggle={onVoiceToggle} />);
    fireEvent.click(screen.getByTestId('voice-btn'));
    expect(onVoiceToggle).toHaveBeenCalledOnce();
  });
});
