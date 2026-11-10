import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// plugin-react liga o JSX automático (sem `import React` em cada arquivo).
export default defineConfig({ plugins: [react()] });
