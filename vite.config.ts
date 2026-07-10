import { defineConfig } from "vite";

export default defineConfig({
  build: {
    emptyOutDir: true,
    minify: false,
    outDir: "extension/dist",
    sourcemap: true,
    rollupOptions: {
      input: {
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
