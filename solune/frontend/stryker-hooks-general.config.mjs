import baseConfig from './stryker.config.mjs';

/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
export default {
  ...baseConfig,
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
  htmlReporter: {
    fileName: 'reports/mutation/hooks-general/mutation-report.html',
  },
};
