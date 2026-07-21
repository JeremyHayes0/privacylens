import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Importing defineConfig from "vitest/config" (rather than plain
// "vite") is the officially documented way to get the `test` field
// typed here -- it re-exports Vite's own defineConfig merged with
// Vitest's config shape, so this file still works as an ordinary Vite
// config for `vite dev`/`vite build`.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
