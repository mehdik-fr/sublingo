import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { defineConfig, loadEnv, type Plugin } from "vite";

type ExtensionEnvironment = "local" | "staging" | "production";

type ExtensionBuildConfig = {
  environment: ExtensionEnvironment;
  backendBaseUrl: string;
  requestTimeoutMs: number;
  maxRetries: number;
};

export default defineConfig(({ mode }) => {
  const buildConfig = resolveBuildConfig(mode);

  return {
    define: {
      __SUBLINGO_BUILD_CONFIG__: JSON.stringify(buildConfig)
    },
    plugins: [emitExtensionPackage(buildConfig)],
    build: {
      emptyOutDir: true,
      minify: mode === "production",
      outDir: "extension/dist",
      sourcemap: mode !== "production",
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
  };
});

function resolveBuildConfig(mode: string): ExtensionBuildConfig {
  if (!isViteBuildMode(mode)) {
    throw new Error(`Unsupported extension build environment: ${mode}`);
  }

  const buildEnvironment: ExtensionEnvironment = mode === "development" ? "local" : mode;
  const environment = loadEnv(mode, process.cwd(), "SUBLINGO_");
  const configuredBaseUrl = environment.SUBLINGO_BACKEND_BASE_URL?.trim();

  if (buildEnvironment !== "local" && !configuredBaseUrl) {
    throw new Error(
      `SUBLINGO_BACKEND_BASE_URL is required for the ${buildEnvironment} build`
    );
  }

  const backendBaseUrl = normalizeBackendBaseUrl(
    configuredBaseUrl || "http://127.0.0.1:8765",
    buildEnvironment
  );
  const defaultTimeout = buildEnvironment === "local" ? 180_000 : 15_000;

  return {
    environment: buildEnvironment,
    backendBaseUrl,
    requestTimeoutMs: parseIntegerInRange(
      environment.SUBLINGO_REQUEST_TIMEOUT_MS,
      defaultTimeout,
      "SUBLINGO_REQUEST_TIMEOUT_MS",
      1,
      300_000
    ),
    maxRetries: parseIntegerInRange(
      environment.SUBLINGO_MAX_RETRIES,
      buildEnvironment === "local" ? 0 : 1,
      "SUBLINGO_MAX_RETRIES",
      0,
      3
    )
  };
}

function emitExtensionPackage(config: ExtensionBuildConfig): Plugin {
  return {
    name: "sublingo-extension-package",
    generateBundle() {
      const manifest = JSON.parse(
        readFileSync(resolve("extension/manifest.json"), "utf8")
      ) as Record<string, unknown>;
      const action = manifest.action as Record<string, unknown>;
      const background = manifest.background as Record<string, unknown>;
      const contentScripts = manifest.content_scripts as Array<Record<string, unknown>>;
      const backendOrigin = new URL(config.backendBaseUrl).origin;

      action.default_popup = "popup.html";
      background.service_worker = "background.js";
      contentScripts.forEach((entry) => {
        entry.js = ["content.js"];
      });
      manifest.host_permissions = [`${backendOrigin}/*`];

      const popupHtml = readFileSync(resolve("extension/popup.html"), "utf8").replace(
        "./dist/popup.js",
        "./popup.js"
      );

      this.emitFile({
        type: "asset",
        fileName: "manifest.json",
        source: `${JSON.stringify(manifest, null, 2)}\n`
      });
      this.emitFile({ type: "asset", fileName: "popup.html", source: popupHtml });
      this.emitFile({
        type: "asset",
        fileName: "popup.css",
        source: readFileSync(resolve("extension/popup.css"), "utf8")
      });
    }
  };
}

function normalizeBackendBaseUrl(
  value: string,
  environment: ExtensionEnvironment
): string {
  const parsed = new URL(value);

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("SUBLINGO_BACKEND_BASE_URL must use HTTP or HTTPS");
  }

  if (parsed.pathname !== "/" || parsed.search || parsed.hash) {
    throw new Error("SUBLINGO_BACKEND_BASE_URL must contain an origin without a path");
  }

  if (environment !== "local" && parsed.protocol !== "https:") {
    throw new Error("Staging and production backend URLs must use HTTPS");
  }

  if (environment === "production" && ["localhost", "127.0.0.1"].includes(parsed.hostname)) {
    throw new Error("The production backend URL cannot target localhost");
  }

  return parsed.origin;
}

function parseIntegerInRange(
  value: string | undefined,
  fallback: number,
  name: string,
  minimum: number,
  maximum: number
): number {
  if (!value) {
    return fallback;
  }

  const parsed = Number(value);

  if (!Number.isSafeInteger(parsed) || parsed < minimum || parsed > maximum) {
    throw new Error(`${name} must be an integer from ${minimum} to ${maximum}`);
  }

  return parsed;
}

function isViteBuildMode(
  value: string
): value is "development" | "staging" | "production" {
  return value === "development" || value === "staging" || value === "production";
}
