import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { SystemMessage } from './SystemMessage';
import type { ChatMessage } from '@/types';

function createMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    message_id: 'msg-1',
    session_id: 'session-1',
    sender_type: 'system',
    content: '✅ Parent issue created: [#42](https://github.com/octocat/hello-world/issues/42)',
    timestamp: '2026-04-08T12:00:00Z',
    ...overrides,
  };
}

describe('SystemMessage', () => {
  it('renders markdown links as clickable anchors', () => {
    render(<SystemMessage message={createMessage()} />);

    expect(screen.getByRole('link', { name: '#42' })).toHaveAttribute(
      'href',
      'https://github.com/octocat/hello-world/issues/42'
    );
  });

  it('still renders plain text content', () => {
    render(<SystemMessage message={createMessage({ content: 'Pipeline started successfully.' })} />);

    expect(screen.getByText('Pipeline started successfully.')).toBeInTheDocument();
  });
});