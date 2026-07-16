export type ExtensionBuildEnvironment = "local" | "staging" | "production";

export type ExtensionBuildConfig = {
  environment: ExtensionBuildEnvironment;
  backendBaseUrl: string;
  requestTimeoutMs: number;
  maxRetries: number;
};

declare const __SUBLINGO_BUILD_CONFIG__: ExtensionBuildConfig;

const localTestFallback: ExtensionBuildConfig = {
  environment: "local",
  backendBaseUrl: "http://127.0.0.1:8765",
  requestTimeoutMs: 180_000,
  maxRetries: 0
};

export const BUILD_CONFIG =
  typeof __SUBLINGO_BUILD_CONFIG__ === "undefined"
    ? localTestFallback
    : __SUBLINGO_BUILD_CONFIG__;

export const BACKEND_ANALYZE_URL =
  `${BUILD_CONFIG.backendBaseUrl}/v1/subtitles/analyze`;
