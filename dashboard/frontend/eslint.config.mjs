// eslint.config.mjs — dashboard/frontend
import js from '@eslint/js';
import globals from 'globals';
import react from 'eslint-plugin-react';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['coverage/', 'dist/'] },
  js.configs.recommended,
  tseslint.configs.recommended,
  react.configs.flat.recommended,
  react.configs.flat['jsx-runtime'],
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: { ...globals.browser },
    },
    settings: { react: { version: 'detect' } },
    linterOptions: { reportUnusedDisableDirectives: 'error' },
    rules: {
      'react/react-in-jsx-scope': 'off',
      '@typescript-eslint/no-explicit-any': 'warn',
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],
    },
  },
  {
    // Node scripts (not linted by the legacy --ext ts,tsx script)
    files: ['scripts/**/*.{js,mjs,cjs}'],
    languageOptions: { globals: { ...globals.node } },
  },
);
