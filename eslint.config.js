import js from '@eslint/js';
import globals from 'globals';

export default [
  {ignores:['dist/**','node_modules/**','tmp/**','playwright-report/**','test-results/**']},
  {files:['src/**/*.{js,jsx}','scripts/**/*.mjs','tests/**/*.mjs','*.js'],
    languageOptions:{globals:{...globals.browser,...globals.node},parserOptions:{ecmaFeatures:{jsx:true}}},
    rules:{...js.configs.recommended.rules,'no-unused-vars':['error',{varsIgnorePattern:'^[A-Z]',argsIgnorePattern:'^_'}]}}
];
