/**
 * Build smoke tests — verify critical modules import and export correctly.
 *
 * These tests catch broken imports, missing exports, and configuration issues
 * that would cause the application to fail at build time or runtime. They
 * complement the TypeScript compiler (`tsc --noEmit`) by verifying that
 * dynamic imports and runtime module resolution work as expected.
 */
import { describe, it, expect } from 'vitest';

describe('Build Smoke Tests', () => {
  describe('Core module imports', () => {
    it('imports the main App component', async () => {
      const mod = await import('@/App');
      expect(mod.default).toBeDefined();
    });

    it('imports the API service module', async () => {
      const mod = await import('@/services/api');
      expect(mod).toBeDefined();
    });

    it('imports lib/utils', async () => {
      const mod = await import('@/lib/utils');
      expect(mod.cn).toBeDefined();
    });
  });

  describe('Page module imports', () => {
    it('imports ProjectsPage', async () => {
      const mod = await import('@/pages/ProjectsPage');
      expect(mod.ProjectsPage).toBeDefined();
    });

    it('imports AgentsPage', async () => {
      const mod = await import('@/pages/AgentsPage');
      expect(mod.AgentsPage).toBeDefined();
    });

    it('imports AgentsPipelinePage', async () => {
      const mod = await import('@/pages/AgentsPipelinePage');
      expect(mod.AgentsPipelinePage).toBeDefined();
    });

    it('imports ChoresPage', async () => {
      const mod = await import('@/pages/ChoresPage');
      expect(mod.ChoresPage).toBeDefined();
    });

    it('imports SettingsPage', async () => {
      const mod = await import('@/pages/SettingsPage');
      expect(mod.SettingsPage).toBeDefined();
    });

    it('imports HelpPage', async () => {
      const mod = await import('@/pages/HelpPage');
      expect(mod.HelpPage).toBeDefined();
    });

    it('imports LoginPage', async () => {
      const mod = await import('@/pages/LoginPage');
      expect(mod.LoginPage).toBeDefined();
    });

    it('imports NotFoundPage', async () => {
      const mod = await import('@/pages/NotFoundPage');
      expect(mod.NotFoundPage).toBeDefined();
    });

    it('imports AppsPage', async () => {
      const mod = await import('@/pages/AppsPage');
      expect(mod.AppsPage).toBeDefined();
    });

    it('imports AppPage', async () => {
      const mod = await import('@/pages/AppPage');
      expect(mod.AppPage).toBeDefined();
    });

    it('imports ToolsPage', async () => {
      const mod = await import('@/pages/ToolsPage');
      expect(mod.ToolsPage).toBeDefined();
    });

    it('imports ActivityPage', async () => {
      const mod = await import('@/pages/ActivityPage');
      expect(mod.ActivityPage).toBeDefined();
    });
  });

  describe('Hook exports', () => {
    it('exports useAuth hook', async () => {
      const mod = await import('@/hooks/useAuth');
      expect(mod.useAuth).toBeDefined();
    });

    it('exports useProjects hook', async () => {
      const mod = await import('@/hooks/useProjects');
      expect(mod.useProjects).toBeDefined();
    });
  });

  describe('Utility module exports', () => {
    it('exports formatAgentName', async () => {
      const mod = await import('@/utils/formatAgentName');
      expect(mod.formatAgentName).toBeDefined();
    });

    it('exports getErrorHint', async () => {
      const mod = await import('@/utils/errorHints');
      expect(mod.getErrorHint).toBeDefined();
    });

    it('exports rateLimit utilities', async () => {
      const mod = await import('@/utils/rateLimit');
      expect(mod.extractRateLimitInfo).toBeDefined();
      expect(mod.isRateLimitApiError).toBeDefined();
    });
  });

  describe('Schema validation modules', () => {
    it('imports service schemas without error', async () => {
      const schemas = await import('@/services/schemas/validate');
      expect(schemas).toBeDefined();
    });
  });

  describe('Component library imports', () => {
    it('imports Button component', async () => {
      const mod = await import('@/components/ui/button');
      expect(mod.Button).toBeDefined();
    });

    it('imports Input component', async () => {
      const mod = await import('@/components/ui/input');
      expect(mod.Input).toBeDefined();
    });
  });
});
