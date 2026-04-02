import baseConfig from './stryker.config.mjs';

/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
export default {
  ...baseConfig,
  mutate: [
    'src/lib/**/*.ts',
    '!src/lib/**/*.test.ts',
    '!src/lib/**/*.property.test.ts',
  ],
  htmlReporter: {
    fileName: 'reports/mutation/lib/mutation-report.html',
  },
};
