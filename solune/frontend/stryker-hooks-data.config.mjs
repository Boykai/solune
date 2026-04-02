import baseConfig from './stryker.config.mjs';

/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
export default {
  ...baseConfig,
  mutate: [
    'src/hooks/useProjects.ts',
    'src/hooks/useChat.ts',
    'src/hooks/useChatHistory.ts',
    'src/hooks/useCommands.ts',
    'src/hooks/useWorkflow.ts',
    'src/hooks/useSettingsForm.ts',
    'src/hooks/useAuth.ts',
  ],
  htmlReporter: {
    fileName: 'reports/mutation/hooks-data/mutation-report.html',
  },
};
