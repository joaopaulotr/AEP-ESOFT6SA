import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// plugin-react liga o JSX automático (sem `import React` em cada arquivo).
// `test`: Vitest só para os testes unitários em src/ (e2e/ é do Playwright).
export default defineConfig({
    plugins: [react()],
    test: { include: ["src/**/*.test.{js,jsx}"], environment: "node" },
});
