const SETTINGS_KEY = "settings";

type ExtensionSettings = {
  enabled: boolean;
};

const defaultSettings: ExtensionSettings = {
  enabled: true
};

const enableToggle = mustQuery<HTMLInputElement>("[data-enable-toggle]");
const toggleLabel = mustQuery<HTMLElement>("[data-toggle-label]");
const toggleHint = mustQuery<HTMLElement>("[data-toggle-hint]");

void bootstrap();

async function bootstrap(): Promise<void> {
  const settings = await readSettings();
  renderToggle(settings);
  enableToggle.addEventListener("change", handleToggleChange);
}

async function handleToggleChange(): Promise<void> {
  const settings: ExtensionSettings = {
    enabled: enableToggle.checked
  };

  await chrome.storage.sync.set({
    [SETTINGS_KEY]: settings
  });

  renderToggle(settings);
}

async function readSettings(): Promise<ExtensionSettings> {
  const result = await chrome.storage.sync.get(SETTINGS_KEY);
  const value = result[SETTINGS_KEY];

  if (isRecord(value) && typeof value.enabled === "boolean") {
    return {
      enabled: value.enabled
    };
  }

  return defaultSettings;
}

function renderToggle(settings: ExtensionSettings): void {
  enableToggle.checked = settings.enabled;
  if (settings.enabled) {
    toggleLabel.textContent = "Sublingo is active";
    toggleHint.textContent = "Interactive subtitles are enabled on supported pages.";
    return;
  }

  toggleLabel.textContent = "Sublingo is inactive";
  toggleHint.textContent = "Turn it back on to restore interactive subtitles.";
}

function mustQuery<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector);

  if (!element) {
    throw new Error(`Missing popup element: ${selector}`);
  }

  return element;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
