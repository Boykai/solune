/**
 * Unified Stryker mutation testing configuration.
 *
 * Supports shard selection via the STRYKER_SHARD environment variable:
 *   STRYKER_SHARD=hooks-board npx stryker run
 *   STRYKER_SHARD=hooks-data  npx stryker run
 *   STRYKER_SHARD=hooks-general npx stryker run
 *   STRYKER_SHARD=lib         npx stryker run
 *
 * When STRYKER_SHARD is not set, all mutation targets are included (full run).
 *
 * @type {import('@stryker-mutator/api/core').PartialStrykerOptions}
 */

const shards = {
  'hooks-board': {
    mutate: [
      'src/hooks/useAdaptivePolling.ts',
      'src/hooks/useBoardProjection.ts',
      'src/hooks/useBoardRefresh.ts',
      'src/hooks/useProjectBoard.ts',
      'src/hooks/useRealTimeSync.ts',
    ],
    reportDir: 'reports/mutation/hooks-board',
  },
  'hooks-data': {
    mutate: [
      'src/hooks/useProjects.ts',
      'src/hooks/useChat.ts',
      'src/hooks/useChatHistory.ts',
      'src/hooks/useCommands.ts',
      'src/hooks/useWorkflow.ts',
      'src/hooks/useSettingsForm.ts',
      'src/hooks/useAuth.ts',
    ],
    reportDir: 'reports/mutation/hooks-data',
  },
  'hooks-general': {
    mutate: [
      'src/hooks/**/*.ts',
      '!src/hooks/**/*.test.ts',
      '!src/hooks/**/*.property.test.ts',
      '!src/hooks/useAdaptivePolling.ts',
      '!src/hooks/useBoardProjection.ts',
      '!src/hooks/useBoardRefresh.ts',
      '!src/hooks/useProjectBoard.ts',
      '!src/hooks/useRealTimeSync.ts',
      '!src/hooks/useProjects.ts',
      '!src/hooks/useChat.ts',
      '!src/hooks/useChatHistory.ts',
      '!src/hooks/useCommands.ts',
      '!src/hooks/useWorkflow.ts',
      '!src/hooks/useSettingsForm.ts',
      '!src/hooks/useAuth.ts',
    ],
    reportDir: 'reports/mutation/hooks-general',
  },
  lib: {
    mutate: [
      'src/lib/**/*.ts',
      '!src/lib/**/*.test.ts',
      '!src/lib/**/*.property.test.ts',
    ],
    reportDir: 'reports/mutation/lib',
  },
};

const shard = process.env.STRYKER_SHARD;

const shardConfig = shard ? shards[shard] : undefined;

if (shard && !shardConfig) {
  const valid = Object.keys(shards).join(', ');
  throw new Error(`Unknown STRYKER_SHARD "${shard}". Valid shards: ${valid}`);
}

const mutate = shardConfig
  ? shardConfig.mutate
  : [
      'src/hooks/**/*.ts',
      'src/lib/**/*.ts',
      '!src/**/*.test.ts',
      '!src/**/*.property.test.ts',
    ];

const reportFileName = shardConfig
  ? `${shardConfig.reportDir}/mutation-report.html`
  : 'reports/mutation/mutation-report.html';

export default {
  testRunner: 'vitest',
  mutate,
  reporters: ['html', 'clear-text', 'progress'],
  htmlReporter: {
    fileName: reportFileName,
  },
  thresholds: {
    high: 80,
    low: 60,
    break: null,
  },
  ignoreStatic: true,
  timeoutMS: 30000,
  timeoutFactor: 2.5,
  concurrency: 4,
};
