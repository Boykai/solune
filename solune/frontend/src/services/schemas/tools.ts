import { z } from 'zod';

export const CatalogInstallConfigSchema = z.object({
  transport: z.string(),
  url: z.string().nullish(),
  command: z.string().nullish(),
  args: z.array(z.string()).optional().default([]),
  env: z.record(z.string(), z.unknown()).optional().default({}),
  headers: z.record(z.string(), z.unknown()).optional().default({}),
  tools: z.array(z.string()).optional().default([]),
});

export const CatalogMcpServerSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  repo_url: z.string().nullish(),
  category: z.string().nullish(),
  server_type: z.string(),
  install_config: CatalogInstallConfigSchema,
  quality_score: z.string().nullish(),
  already_installed: z.boolean(),
});

export const CatalogMcpServerListResponseSchema = z.object({
  servers: z.array(CatalogMcpServerSchema),
  count: z.number(),
  query: z.string().nullish(),
  category: z.string().nullish(),
});
