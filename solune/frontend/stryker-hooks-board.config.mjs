import baseConfig from './stryker.config.mjs';

/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
export default {
  ...baseConfig,
  mutate: [
    'src/hooks/useAdaptivePolling.ts',
    'src/hooks/useBoardProjection.ts',
    'src/hooks/useBoardRefresh.ts',
    'src/hooks/useProjectBoard.ts',
    'src/hooks/useRealTimeSync.ts',
  ],
  htmlReporter: {
    fileName: 'reports/mutation/hooks-board/mutation-report.html',
  },
};
