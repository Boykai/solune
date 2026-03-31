import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const currentDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(currentDir, '../../..');
const docsRoot = resolve(repoRoot, 'docs');

const changedDocs = [
  'api-reference.md',
  'architecture.md',
  'project-structure.md',
  'roadmap.md',
  'pages/README.md',
  'pages/chat.md',
  'pages/layout.md',
] as const;

const relativeLinkPattern = /(?<!!)\[[^\]]+\]\(([^)]+)\)/g;

function readDoc(relativePath: string): string {
  return readFileSync(resolve(docsRoot, relativePath), 'utf8');
}

function slugifyHeading(heading: string): string {
  return heading
    .trim()
    .toLowerCase()
    .replace(/<[^>]+>/g, '')
    .replace(/[`*_~]/g, '')
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-');
}

function extractHeadingSlugs(markdown: string): Set<string> {
  const headings = markdown.match(/^#{1,6}\s+.+$/gm) ?? [];

  return new Set(headings.map((heading) => slugifyHeading(heading.replace(/^#{1,6}\s+/, ''))));
}

function getRelativeMarkdownLinks(markdown: string): string[] {
  return Array.from(markdown.matchAll(relativeLinkPattern), (match) => match[1].trim()).filter((link) => {
    return link.endsWith('.md') || link.includes('.md#') || link.startsWith('#');
  });
}

describe('chat documentation updates', () => {
  it('keeps the new chat guide linked from the pages index and layout guide', () => {
    const pagesIndex = readDoc('pages/README.md');
    const layoutGuide = readDoc('pages/layout.md');
    const chatGuide = readDoc('pages/chat.md');

    expect(chatGuide).toContain('# Chat');
    expect(pagesIndex).toContain('[Chat](chat.md)');
    expect(layoutGuide).toContain('[Chat](chat.md)');
  });

  it('documents the streaming chat API and attachment constraints', () => {
    const apiReference = readDoc('api-reference.md');

    expect(apiReference).toContain('POST | `/chat/messages/stream`');
    expect(apiReference).toContain('Requires `ai_enhance=true`');
    expect(apiReference).toContain('`token`');
    expect(apiReference).toContain('`tool_call`');
    expect(apiReference).toContain('`tool_result`');
    expect(apiReference).toContain('`done`');
    expect(apiReference).toContain('`error`');
    expect(apiReference).toContain('10 requests per minute');
    expect(apiReference).toContain('Maximum files per message | 5');
    expect(apiReference).toContain('Maximum file size | 10 MB per file');
    expect(apiReference).toContain('`.vtt` and `.srt` files are automatically detected as transcripts');
  });

  it('documents the new chat architecture and project structure entries', () => {
    const architecture = readDoc('architecture.md');
    const projectStructure = readDoc('project-structure.md');

    expect(architecture).toContain('### ChatAgentService');
    expect(architecture).toContain('MentionInput');
    expect(architecture).toContain('MentionAutocomplete');
    expect(architecture).toContain('FilePreviewChips');
    expect(architecture).toContain('MarkdownRenderer');
    expect(architecture).toContain('ChatMessageSkeleton');
    expect(architecture).toContain('PipelineWarningBanner');
    expect(architecture).toContain('PipelineIndicator');
    expect(architecture).toContain('useChatProposals');
    expect(architecture).toContain('useFileUpload');
    expect(architecture).toContain('useMentionAutocomplete');

    expect(projectStructure).toContain('chat_agent.py');
    expect(projectStructure).toContain('MentionInput');
    expect(projectStructure).toContain('MentionAutocomplete');
    expect(projectStructure).toContain('FilePreviewChips');
    expect(projectStructure).toContain('MarkdownRenderer');
    expect(projectStructure).toContain('ChatMessageSkeleton');
    expect(projectStructure).toContain('PipelineWarningBanner');
    expect(projectStructure).toContain('PipelineIndicator');
    expect(projectStructure).toContain('useChatProposals');
    expect(projectStructure).toContain('useFileUpload');
    expect(projectStructure).toContain('useMentionAutocomplete');
  });

  it('marks the shipped v0.2.0 chat capabilities in the roadmap', () => {
    const roadmap = readDoc('roadmap.md');

    expect(roadmap).toContain('✅ **Agent Framework chat agent**');
    expect(roadmap).toContain('✅ **Streaming responses**');
    expect(roadmap).toContain('✅ **File uploads**');
    expect(roadmap).toContain('✅ **@mention pipeline selection**');
    expect(roadmap).toContain('✅ **AI Enhance toggle**');
    expect(roadmap).toContain('✅ **Chat history navigation**');
    expect(roadmap).toContain('✅ **Markdown rendering**');
    expect(roadmap).toContain('v0.2.0 (current)');
    expect(roadmap).toContain('| **v0.2.0** | Microsoft Agent Framework chat | ✅ Shipped |');
  });

  it('resolves all relative markdown links in the changed docs', () => {
    const brokenLinks: string[] = [];

    for (const relativeDocPath of changedDocs) {
      const sourcePath = resolve(docsRoot, relativeDocPath);
      const markdown = readFileSync(sourcePath, 'utf8');
      const sourceDir = dirname(sourcePath);

      for (const link of getRelativeMarkdownLinks(markdown)) {
        const [rawTargetPath, rawFragment] = link.split('#', 2);
        const targetPath = rawTargetPath ? resolve(sourceDir, rawTargetPath) : sourcePath;

        if (!existsSync(targetPath)) {
          brokenLinks.push(`${relativeDocPath} -> ${link} (missing file)`);
          continue;
        }

        if (!rawFragment) {
          continue;
        }

        const targetMarkdown = readFileSync(targetPath, 'utf8');
        const headingSlugs = extractHeadingSlugs(targetMarkdown);
        if (!headingSlugs.has(rawFragment)) {
          brokenLinks.push(`${relativeDocPath} -> ${link} (missing heading #${rawFragment})`);
        }
      }
    }

    expect(brokenLinks).toEqual([]);
  });
});
