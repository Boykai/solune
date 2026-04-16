import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import security from 'eslint-plugin-security';

export default tseslint.config(
  { ignores: ['dist', 'build', 'node_modules', 'coverage', 'test-results', 'e2e-report'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    plugins: {
      'react-hooks': reactHooks,
      'jsx-a11y': jsxA11y,
      security,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.configs.recommended.rules,
      ...security.configs.recommended.rules,
      // reason: detect-object-injection produces excessive false positives on all bracket access
      'security/detect-object-injection': 'off',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'jsx-a11y/label-has-associated-control': ['error', {
        assert: 'either',
        depth: 3,
      }],
      'no-restricted-imports': ['error', {
        paths: [{
          name: 'lucide-react',
          message: 'Import icons from @/lib/icons instead of lucide-react directly.',
        }],
      }],
    },
  },
  {
    files: ['**/*.test.{ts,tsx}'],
    rules: {
      // reason: test fixtures use dynamic file paths that trigger false positives
      'security/detect-non-literal-fs-filename': 'off',
      // reason: test data may contain intentional regex patterns
      'security/detect-unsafe-regex': 'off',
    },
  },
  {
    files: ['e2e/**/*.{ts,tsx}'],
    rules: {
      // reason: Playwright fixtures use dynamic file paths
      'security/detect-non-literal-fs-filename': 'off',
      // reason: Playwright `use()` callback triggers false positives for hooks detection
      'react-hooks/rules-of-hooks': 'off',
    },
  },
  {
    files: ['src/lib/icons.ts'],
    rules: {
      // reason: icons.ts is the canonical re-export barrel; it must import from lucide-react
      'no-restricted-imports': 'off',
    },
  }
);
