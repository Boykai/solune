import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const currentDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(currentDir, '../../..');
const docsRoot = resolve(repoRoot, 'docs');

const changedDocs = [
  '.change-manifest.md',
  'OWNERS.md',
  'api-reference.md',
  'architecture.md',
  'checklists/doc-refresh-verification.md',
  'project-structure.md',
  'roadmap.md',
  'pages/README.md',
  'pages/chat.md',
  'pages/dashboard.md',
  'pages/layout.md',
  'testing.md',
] as const;

const relativeLinkPattern = /(?<!!)\[[^\]]+\]\(([^)]+)\)/g;

function readDoc(relativePath: string): string {
  return readFileSync(resolve(docsRoot, relativePath), 'utf8');
}

function slugifyHeading(heading: string): string {
  return heading
    .trim()
    .toLowerCase()
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

function collectBrokenRelativeLinks(rootPath: string, relativePaths: readonly string[]): string[] {
  const brokenLinks: string[] = [];

  for (const relativePath of relativePaths) {
    const sourcePath = resolve(rootPath, relativePath);
    const markdown = readFileSync(sourcePath, 'utf8');
    const sourceDir = dirname(sourcePath);

    for (const link of getRelativeMarkdownLinks(markdown)) {
      const [rawTargetPath, rawFragment] = link.split('#', 2);
      const targetPath = rawTargetPath ? resolve(sourceDir, rawTargetPath) : sourcePath;

      if (!existsSync(targetPath)) {
        brokenLinks.push(`${relativePath} -> ${link} (missing file)`);
        continue;
      }

      if (!rawFragment) {
        continue;
      }

      const targetMarkdown = readFileSync(targetPath, 'utf8');
      const headingSlugs = extractHeadingSlugs(targetMarkdown);
      if (!headingSlugs.has(rawFragment)) {
        brokenLinks.push(`${relativePath} -> ${link} (missing heading #${rawFragment})`);
      }
    }
  }

  return brokenLinks;
}

function extractSection(markdown: string, heading: string): string {
  const startToken = `## ${heading}\n`;
  const startIndex = markdown.indexOf(startToken);

  if (startIndex === -1) {
    return '';
  }

  const remainingMarkdown = markdown.slice(startIndex + startToken.length).trimStart();
  const nextHeadingIndex = remainingMarkdown.search(/\n## /);

  return nextHeadingIndex === -1 ? remainingMarkdown : remainingMarkdown.slice(0, nextHeadingIndex);
}

function extractChecklistItems(markdown: string, heading: string): string[] {
  const section = extractSection(markdown, heading);

  return Array.from(section.matchAll(/^- \[[ x]\] (.+)$/gm), (match) => match[1].trim());
}

function extractAffectedDocs(markdown: string): string[] {
  return Array.from(markdown.matchAll(/Affected Docs: (.+)$/gm), (match) => match[1])
    .flatMap((docs) => docs.split(','))
    .map((docPath) => docPath.trim())
    .filter(Boolean);
}

describe('chat documentation updates', () => {
  it('keeps the new chat guide linked from the pages index and layout guide', () => {
    const pagesIndex = readDoc('pages/README.md');
    const layoutGuide = readDoc('pages/layout.md');
    const chatGuide = readDoc('pages/chat.md');
    const dashboardGuide = readDoc('pages/dashboard.md');

    expect(chatGuide).toContain('# Chat');
    expect(chatGuide).toContain('no dedicated `/chat` route');
    expect(chatGuide).toContain('ChatPopup');
    expect(chatGuide).toContain('ChatPanelManager');
    expect(pagesIndex).toContain('[Chat](chat.md)');
    expect(layoutGuide).toContain('[Chat](chat.md)');
    expect(dashboardGuide).toContain('full-screen chat workspace');
    expect(dashboardGuide).toContain('solune:chat-panels');
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
    expect(architecture).toContain('ActivityPage');
    expect(architecture).toContain('AppsPage');
    expect(architecture).toContain('HelpPage');
    expect(architecture).toContain('useConversations');
    expect(architecture).toContain('app_plan_orchestrator');
    expect(architecture).toContain('plan_agent_provider');
    expect(architecture).toContain('transcript_detector');

    expect(projectStructure).toContain('044_conversations.sql');
    expect(projectStructure).toContain('command-palette/');
    expect(projectStructure).toContain('onboarding/');
    expect(projectStructure).toContain('useConversations');
    expect(projectStructure).toContain('activity_service.py');
    expect(projectStructure).toContain('task_registry.py');
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
    expect(roadmap).toContain('v0.2.0 — Intelligent Chat Agent (current)');
    expect(roadmap).toContain('| **v0.2.0** | Microsoft Agent Framework chat | ✅ Shipped |');
    expect(roadmap).toContain('Aspirational');
  });

  it('documents configuration additions and frontend docs', () => {
    const configuration = readDoc('configuration.md');
    const testing = readDoc('testing.md');
    const frontendReadme = readFileSync(resolve(repoRoot, 'frontend/README.md'), 'utf8');

    expect(configuration).toContain('AGENT_SESSION_TTL_SECONDS');
    expect(configuration).toContain('AGENT_MAX_CONCURRENT_SESSIONS');
    expect(configuration).toContain('AGENT_STREAMING_ENABLED');
    expect(configuration).toContain('AGENT_COPILOT_TIMEOUT_SECONDS');
    expect(configuration).toContain('CHAT_AUTO_CREATE_ENABLED');
    expect(configuration).toContain('OTEL_EXPORTER_OTLP_ENDPOINT');
    expect(configuration).toContain('SENTRY_DSN');
    expect(configuration).toContain('MCP_SERVER_ENABLED');
    expect(configuration).toContain('API_TIMEOUT_SECONDS');

    expect(testing).toContain('backend/tests/');
    expect(testing).toContain('chaos/');
    expect(testing).toContain('frontend/e2e/');
    expect(frontendReadme).toContain('# Solune Frontend');
    expect(frontendReadme).toContain('React 19');
    expect(frontendReadme).toContain('TanStack Query v5');
    expect(frontendReadme).toContain('npm run build');
  });

  it('resolves all relative markdown links in the changed docs', () => {
    expect(collectBrokenRelativeLinks(docsRoot, changedDocs)).toEqual([]);
  });
});

describe('librarian documentation workflow', () => {
  it('keeps the verification checklist template aligned with the manifest checklist', () => {
    const checklistTemplate = readDoc('checklists/doc-refresh-verification.md');
    const changeManifest = readDoc('.change-manifest.md');

    expect(extractChecklistItems(changeManifest, 'Verification Checklist')).toEqual(
      extractChecklistItems(checklistTemplate, 'Verification Items'),
    );
    expect(checklistTemplate).toContain('## Overall Status');
    expect(changeManifest).toContain('**Overall Status**: PASS');
  });

  it('references only existing documentation files in the change manifest', () => {
    const changeManifest = readDoc('.change-manifest.md');
    const affectedDocs = extractAffectedDocs(changeManifest);

    expect(affectedDocs).not.toEqual([]);
    expect(affectedDocs.filter((docPath) => !existsSync(resolve(repoRoot, docPath)))).toEqual([]);
  });
});
