import { describe, it, expect } from 'vitest';
import {
  CatalogMcpServerSchema,
  CatalogMcpServerListResponseSchema,
  CatalogInstallConfigSchema,
} from '@/services/schemas/tools';

describe('CatalogMcpServer Zod schema', () => {
  it('validates a complete catalog server', () => {
    const result = CatalogMcpServerSchema.safeParse({
      id: 'github-mcp',
      name: 'GitHub MCP',
      description: 'GitHub integration',
      repo_url: 'https://github.com/github/github-mcp-server',
      category: 'Developer Tools',
      server_type: 'http',
      install_config: {
        transport: 'http',
        url: 'https://api.githubcopilot.com/mcp',
      },
      quality_score: 'A',
      already_installed: false,
    });
    expect(result.success).toBe(true);
  });

  it('validates a minimal catalog server', () => {
    const result = CatalogMcpServerSchema.safeParse({
      id: 'test',
      name: 'Test',
      description: 'Test server',
      server_type: 'stdio',
      install_config: { transport: 'stdio', command: 'npx' },
      already_installed: false,
    });
    expect(result.success).toBe(true);
  });

  it('rejects a server missing required fields', () => {
    const result = CatalogMcpServerSchema.safeParse({
      id: 'test',
      // missing name
      description: 'Test server',
      server_type: 'http',
      install_config: { transport: 'http' },
      already_installed: false,
    });
    expect(result.success).toBe(false);
  });

  it('rejects a server missing install_config', () => {
    const result = CatalogMcpServerSchema.safeParse({
      id: 'test',
      name: 'Test',
      description: 'Test server',
      server_type: 'http',
      already_installed: false,
    });
    expect(result.success).toBe(false);
  });

  it('rejects when already_installed is not boolean', () => {
    const result = CatalogMcpServerSchema.safeParse({
      id: 'test',
      name: 'Test',
      description: 'Test',
      server_type: 'http',
      install_config: { transport: 'http' },
      already_installed: 'yes',
    });
    expect(result.success).toBe(false);
  });

  it('validates a catalog list response', () => {
    const result = CatalogMcpServerListResponseSchema.safeParse({
      servers: [
        {
          id: 'test',
          name: 'Test',
          description: 'Test',
          server_type: 'http',
          install_config: { transport: 'http', url: 'https://example.com' },
          already_installed: false,
        },
      ],
      count: 1,
      query: 'github',
      category: null,
    });
    expect(result.success).toBe(true);
  });

  it('validates an empty catalog list response', () => {
    const result = CatalogMcpServerListResponseSchema.safeParse({
      servers: [],
      count: 0,
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.servers).toEqual([]);
      expect(result.data.count).toBe(0);
    }
  });

  it('validates install config with all fields', () => {
    const result = CatalogInstallConfigSchema.safeParse({
      transport: 'stdio',
      command: 'npx',
      args: ['-y', 'test-pkg'],
      env: { API_KEY: 'xxx' },
      headers: {},
      tools: ['tool1'],
    });
    expect(result.success).toBe(true);
  });

  it('validates install config with nullable url', () => {
    const result = CatalogInstallConfigSchema.safeParse({
      transport: 'stdio',
      url: null,
      command: 'npx',
    });
    expect(result.success).toBe(true);
  });

  it('applies defaults for optional array/object fields in install config', () => {
    const result = CatalogInstallConfigSchema.safeParse({
      transport: 'http',
      url: 'https://example.com',
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.args).toEqual([]);
      expect(result.data.env).toEqual({});
      expect(result.data.headers).toEqual({});
      expect(result.data.tools).toEqual([]);
    }
  });

  it('rejects install config missing transport', () => {
    const result = CatalogInstallConfigSchema.safeParse({
      url: 'https://example.com',
    });
    expect(result.success).toBe(false);
  });

  it('allows extra fields with default passthrough behavior', () => {
    const result = CatalogMcpServerSchema.safeParse({
      id: 'test',
      name: 'Test',
      description: 'Test',
      server_type: 'http',
      install_config: { transport: 'http' },
      already_installed: false,
      extra_field: 'should be allowed via passthrough',
    });
    expect(result.success).toBe(true);
  });
});
