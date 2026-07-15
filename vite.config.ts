import { defineConfig } from "vite";

export default defineConfig({
  build: {
    emptyOutDir: true,
    minify: false,
    outDir: "extension/dist",
    sourcemap: true,
    rollupOptions: {
      input: {
        background: "extension/src/background.ts",
        content: "extension/src/content.ts",
        popup: "extension/src/popup.ts"
      },
      output: {
        entryFileNames: "[name].js",
        format: "es"
      }
    }
  }
});
