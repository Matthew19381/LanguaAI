import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'

// Flat config (ESLint 9). Minimal but catches the real bug classes:
//  - no-undef: a JSX component/identifier used without import/definition
//    (this is exactly what crashed <Practice> when SpecialChars wasn't imported)
//  - react-hooks rules: conditional/early-return hooks, bad deps
// no-unused-vars ignores Capitalized names because, without eslint-plugin-react,
// components/icons used only inside JSX would otherwise be reported as unused.
export default [
  { ignores: ['dist/**', 'node_modules/**', 'dev-dist/**', 'public/**', '*.config.js'] },
  js.configs.recommended,
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.serviceworker },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      'no-undef': 'error',
      'no-unused-vars': ['warn', { varsIgnorePattern: '^[A-Z_]', argsIgnorePattern: '^_' }],
      // Empty catch is an intentional swallow-and-continue pattern here.
      'no-empty': ['error', { allowEmptyCatch: true }],
      'no-useless-escape': 'warn',
    },
  },
]
