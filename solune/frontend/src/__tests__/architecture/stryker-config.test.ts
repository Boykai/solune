/**
 * Tests for the unified Stryker mutation testing configuration.
 *
 * Verifies the config file structure, shard definitions, unknown-shard
 * error handling, CI workflow alignment, and old config file cleanup.
 *
 * Because Stryker config relies on `process.env` at module-evaluation time,
 * we read the file as text and parse the shard definitions rather than
 * attempting dynamic ESM re-imports that fight module caching.
 */

import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_ROOT = path.resolve(__dirname, '../../../');
const STRYKER_CONFIG_PATH = path.resolve(FRONTEND_ROOT, 'stryker.config.mjs');
const WORKFLOW_PATH = path.resolve(
  FRONTEND_ROOT,
  '../../.github/workflows/mutation-testing.yml',
);

const configSource = fs.readFileSync(STRYKER_CONFIG_PATH, 'utf-8');

describe('stryker.config.mjs', () => {
  it('should exist at the expected location', () => {
    expect(fs.existsSync(STRYKER_CONFIG_PATH)).toBe(true);
  });

  describe('config structure', () => {
    it('should use vitest as the test runner', () => {
      expect(configSource).toContain("testRunner: 'vitest'");
    });

    it('should configure HTML, clear-text, and progress reporters', () => {
      expect(configSource).toContain("'html'");
      expect(configSource).toContain("'clear-text'");
      expect(configSource).toContain("'progress'");
    });

    it('should set ignoreStatic to true', () => {
      expect(configSource).toContain('ignoreStatic: true');
    });

    it('should define threshold configuration', () => {
      expect(configSource).toContain('thresholds');
      expect(configSource).toContain('high: 80');
      expect(configSource).toContain('low: 60');
    });

    it('should export a default config object', () => {
      expect(configSource).toMatch(/export default\s*\{/);
    });
  });

  describe('shard definitions', () => {
    const EXPECTED_SHARDS = [
      'hooks-board',
      'hooks-data',
      'hooks-general',
      'lib',
    ];

    it.each(EXPECTED_SHARDS)(
      'should define the "%s" shard',
      (shard: string) => {
        // Shard keys may be quoted or unquoted in the config source
        const hasQuoted = configSource.includes(`'${shard}'`);
        const hasUnquoted = new RegExp(`\\b${shard.replace('-', '\\-')}\\b`).test(configSource);
        expect(
          hasQuoted || hasUnquoted,
          `Expected shard "${shard}" to be defined in stryker.config.mjs`,
        ).toBe(true);
      },
    );

    it('hooks-board should target board-related hooks', () => {
      expect(configSource).toContain('useProjectBoard');
      expect(configSource).toContain('useBoardRefresh');
      expect(configSource).toContain('useAdaptivePolling');
    });

    it('hooks-data should target data hooks', () => {
      expect(configSource).toContain('useProjects');
      expect(configSource).toContain('useChat');
      expect(configSource).toContain('useWorkflow');
    });

    it('hooks-general should use glob patterns with exclusions', () => {
      expect(configSource).toContain("'src/hooks/**/*.ts'");
      expect(configSource).toContain("'!src/hooks/**/*.test.ts'");
    });

    it('lib shard should target src/lib/**/*.ts', () => {
      expect(configSource).toContain("'src/lib/**/*.ts'");
      expect(configSource).toContain("'!src/lib/**/*.test.ts'");
    });

    it('each shard should have a dedicated report directory', () => {
      for (const shard of EXPECTED_SHARDS) {
        expect(configSource).toContain(`reports/mutation/${shard}`);
      }
    });
  });

  describe('unknown shard handling', () => {
    it('should contain error throwing logic for unknown shards', () => {
      expect(configSource).toContain('Unknown STRYKER_SHARD');
      expect(configSource).toMatch(/throw new Error/);
    });

    it('should list valid shards in the error message', () => {
      expect(configSource).toContain('Valid shards');
    });
  });

  describe('default (full-run) behaviour', () => {
    it('should include both hooks and lib in default mutate patterns', () => {
      // The default (no shard) block should include broad globs
      expect(configSource).toContain("'src/hooks/**/*.ts'");
      expect(configSource).toContain("'src/lib/**/*.ts'");
    });

    it('should use a default report path for full runs', () => {
      expect(configSource).toContain(
        'reports/mutation/mutation-report.html',
      );
    });
  });

  describe('CI workflow alignment', () => {
    it('CI matrix references matching shard names', () => {
      const workflowContent = fs.readFileSync(WORKFLOW_PATH, 'utf-8');

      // Extract frontend shard names from the CI matrix
      const shardRegex = /- (hooks-board|hooks-data|hooks-general|lib)\b/g;
      const ciShards: string[] = [];
      let match;
      while ((match = shardRegex.exec(workflowContent)) !== null) {
        ciShards.push(match[1]);
      }

      expect(ciShards).toContain('hooks-board');
      expect(ciShards).toContain('hooks-data');
      expect(ciShards).toContain('hooks-general');
      expect(ciShards).toContain('lib');
    });

    it('CI uses STRYKER_SHARD env variable', () => {
      const workflowContent = fs.readFileSync(WORKFLOW_PATH, 'utf-8');
      expect(workflowContent).toContain('STRYKER_SHARD=');
    });
  });

  describe('old config cleanup', () => {
    const OLD_CONFIGS = [
      'stryker-hooks-board.config.mjs',
      'stryker-hooks-data.config.mjs',
      'stryker-hooks-general.config.mjs',
      'stryker-lib.config.mjs',
    ];

    it.each(OLD_CONFIGS)(
      'old config "%s" should no longer exist',
      (filename: string) => {
        const fullPath = path.resolve(FRONTEND_ROOT, filename);
        expect(
          fs.existsSync(fullPath),
          `Old config file ${filename} should have been removed`,
        ).toBe(false);
      },
    );
  });
});
