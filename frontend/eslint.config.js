import js from "@eslint/js";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";

export default [
  { ignores: ["dist", "playwright-report", "test-results"] },
  js.configs.recommended,
  {
    files: ["**/*.{js,jsx}"],
    plugins: { react, "react-hooks": reactHooks },
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    settings: { react: { version: "detect" } },
    rules: {
      ...react.configs.recommended.rules,
      ...react.configs["jsx-runtime"].rules,
      // regras do React Compiler (react-hooks v7: refs, immutability, set-state-in-effect) adiadas —
      // padrões atuais funcionam; revisar se adotar o Compiler.
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "react/prop-types": "off",
    },
  },
  {
    // E2E (Playwright) roda em Node, fora do navegador.
    files: ["e2e/**/*.js"],
    languageOptions: { globals: { ...globals.node } },
  },
  {
    files: ["*.config.js"],
    languageOptions: { globals: { ...globals.node } },
  },
];
