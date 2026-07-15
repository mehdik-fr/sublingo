import type { PreparedDictionaryEntry } from "./dictionary";
import {
  clearSubtitleTranslationCache,
  prefetchSubtitleLine,
  translateSubtitleLine,
  type SubtitleTranslation
} from "./translation-client";
import { hasRomanization, isRedundantDefinition } from "./tooltip-content";
import { findEntryAt, isWord, splitSegments } from "./tokenizer";

const ROOT_ID = "sublingo-extension-root";
const INLINE_STYLE_ID = "sublingo-inline-styles";
const SUBTITLE_ROOT_ATTRIBUTE = "data-sublingo-subtitle-root";
const TOKEN_ATTRIBUTE = "data-sublingo-token";
const PLAIN_ATTRIBUTE = "data-sublingo-plain";
const SETTINGS_KEY = "settings";

type ExtensionSettings = {
  enabled: boolean;
  sourceLanguage: string;
  targetLanguage: string;
};

type PlatformAdapter = {
  id: "demo" | "youtube";
  matches: () => boolean;
  getSubtitleRoots: () => HTMLElement[];
};

type SubtitleRootState = {
  isRendering: boolean;
  lastRenderedText: string;
  observer: MutationObserver;
  translation: SubtitleTranslation | null;
  translationError: string | null;
  translationRequestId: number;
};

type TokenTooltipData = {
  kind: "dictionary" | "line";
  source: string;
  target: string;
  romanization: string;
  grammar: string;
  definition: string;
  pronunciation: string;
  lineTranslation: string | null;
  provider: string | null;
  isMock: boolean;
};

type ExtensionState = {
  activePlatformId: PlatformAdapter["id"] | null;
  demoTrackCleanup: (() => void) | null;
  isEnabled: boolean;
  pageObserver: MutationObserver | null;
  rootStates: Map<HTMLElement, SubtitleRootState>;
  tooltipElement: HTMLElement | null;
  hideTooltipTimer: number | null;
  pinnedToken: HTMLElement | null;
  isPlatformSyncScheduled: boolean;
  sourceLanguage: string;
  targetLanguage: string;
};

const platforms: PlatformAdapter[] = [
  {
    id: "demo",
    matches: () => {
      return (
        (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") &&
        window.location.pathname.startsWith("/demo")
      );
    },
    getSubtitleRoots: () => {
      const subtitle = document.querySelector<HTMLElement>("#subtitle");
      return subtitle ? [subtitle] : [];
    }
  },
  {
    id: "youtube",
    matches: () => {
      return window.location.hostname === "www.youtube.com" && window.location.pathname === "/watch";
    },
    getSubtitleRoots: () => {
      return Array.from(
        document.querySelectorAll<HTMLElement>(".ytp-caption-segment:not([data-sublingo-ignore])")
      );
    }
  }
];

const state: ExtensionState = {
  activePlatformId: null,
  demoTrackCleanup: null,
  isEnabled: true,
  pageObserver: null,
  rootStates: new Map(),
  tooltipElement: null,
  hideTooltipTimer: null,
  pinnedToken: null,
  isPlatformSyncScheduled: false,
  sourceLanguage: "fr",
  targetLanguage: "en"
};

function bootstrap(): void {
  createTooltipRoot();
  ensureSubtitleStyles();
  attachGlobalEvents();
  initializeSettings();
}

function createTooltipRoot(): void {
  if (document.getElementById(ROOT_ID)) {
    return;
  }

  const host = document.createElement("div");
  host.id = ROOT_ID;

  const root = host.attachShadow({ mode: "open" });
  root.innerHTML = `
    <style>
      :host {
        all: initial;
        color-scheme: light;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      .tooltip {
        background: rgba(255, 255, 255, 0.98);
        border: 1px solid rgba(17, 24, 39, 0.12);
        border-radius: 8px;
        box-shadow: 0 14px 36px rgba(15, 23, 42, 0.18);
        color: #111827;
        max-width: min(320px, calc(100vw - 32px));
        opacity: 0;
        padding: 12px 14px;
        pointer-events: none;
        position: fixed;
        transform: translateY(4px);
        transition: opacity 120ms ease, transform 120ms ease;
        z-index: 2147483647;
      }

      .tooltip.visible {
        opacity: 1;
        transform: translateY(0);
      }

      .tooltip.pinned {
        border-color: rgba(15, 118, 110, 0.42);
        pointer-events: auto;
      }

      .tooltip-header {
        align-items: flex-start;
        display: flex;
        gap: 12px;
        justify-content: space-between;
      }

      .tooltip-title {
        flex: 1;
        font-size: 14px;
        font-weight: 700;
        line-height: 1.2;
        margin: 0 0 6px;
      }

      .tooltip-close {
        align-items: center;
        background: white;
        border: 1px solid rgba(17, 24, 39, 0.12);
        border-radius: 999px;
        color: #111827;
        cursor: pointer;
        display: inline-flex;
        flex: none;
        height: 24px;
        justify-content: center;
        padding: 0;
        width: 24px;
      }

      .tooltip-grid {
        display: grid;
        gap: 6px;
        grid-template-columns: auto 1fr;
        margin: 12px 0;
      }

      .tooltip-label {
        color: #667085;
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
      }

      .tooltip-value {
        font-size: 13px;
        margin: 0;
      }

      .tooltip-body {
        color: #667085;
        font-size: 13px;
        line-height: 1.45;
        margin: 0;
      }

      .tooltip-line {
        border-top: 1px solid rgba(17, 24, 39, 0.1);
        color: #344054;
        font-size: 13px;
        line-height: 1.45;
        margin: 12px 0 0;
        padding-top: 10px;
      }

      .tooltip-meta {
        color: #98a2b3;
        font-size: 11px;
        margin: 6px 0 0;
      }

      .listen-button {
        background: rgba(15, 118, 110, 0.12);
        border: 0;
        border-radius: 8px;
        color: #0f766e;
        cursor: pointer;
        font: inherit;
        font-weight: 700;
        margin-top: 12px;
        padding: 8px 10px;
      }
    </style>
    <div class="tooltip" data-tooltip hidden></div>
  `;

  document.documentElement.append(host);
  state.tooltipElement = root.querySelector("[data-tooltip]");
}

function ensureSubtitleStyles(): void {
  if (document.getElementById(INLINE_STYLE_ID)) {
    return;
  }

  const style = document.createElement("style");
  style.id = INLINE_STYLE_ID;
  style.textContent = `
    [${SUBTITLE_ROOT_ATTRIBUTE}] .sublingo-token {
      border-radius: 6px;
      cursor: pointer;
      padding: 0.04em 0.08em;
      text-decoration: underline;
      text-decoration-color: rgba(255, 255, 255, 0.34);
      text-decoration-thickness: 2px;
      text-underline-offset: 0.16em;
      transition: background 140ms ease, text-decoration-color 140ms ease;
    }

    [${SUBTITLE_ROOT_ATTRIBUTE}] .sublingo-token:hover,
    [${SUBTITLE_ROOT_ATTRIBUTE}] .sublingo-token:focus-visible {
      background: rgba(255, 255, 255, 0.16);
      outline: none;
      text-decoration-color: #ffffff;
    }

    [${SUBTITLE_ROOT_ATTRIBUTE}] .sublingo-token.sublingo-token-pinned {
      background: rgba(15, 118, 110, 0.46);
      text-decoration-color: #ffffff;
    }
  `;

  document.head.append(style);
}

function attachGlobalEvents(): void {
  document.addEventListener("keydown", handleKeydown);
  document.addEventListener("click", handleDocumentClick, true);
  window.addEventListener("popstate", schedulePlatformSync);
  window.addEventListener("yt-navigate-finish", schedulePlatformSync as EventListener);
  chrome.storage.onChanged.addListener(handleStorageChanged);
}

function startPlatformWatcher(): void {
  if (state.pageObserver) {
    return;
  }

  schedulePlatformSync();

  state.pageObserver = new MutationObserver(() => {
    schedulePlatformSync();
  });

  state.pageObserver.observe(document.documentElement, {
    childList: true,
    subtree: true
  });
}

function schedulePlatformSync(): void {
  if (state.isPlatformSyncScheduled) {
    return;
  }

  state.isPlatformSyncScheduled = true;
  requestAnimationFrame(() => {
    state.isPlatformSyncScheduled = false;
    syncPlatform();
  });
}

function syncPlatform(): void {
  if (!state.isEnabled) {
    disconnectSubtitleRoots(true);
    disconnectDemoTrackBridge();
    state.activePlatformId = null;
    closePinnedTooltip();
    return;
  }

  const platform = platforms.find((candidate) => candidate.matches()) ?? null;
  const nextPlatformId = platform?.id ?? null;

  if (nextPlatformId !== state.activePlatformId) {
    disconnectSubtitleRoots(true);
    disconnectDemoTrackBridge();
    closePinnedTooltip();
    state.activePlatformId = nextPlatformId;
  }

  if (!platform) {
    return;
  }

  if (platform.id === "demo") {
    ensureDemoTrackBridge();
  } else {
    disconnectDemoTrackBridge();
  }

  const roots = platform
    .getSubtitleRoots()
    .filter((element) => element.isConnected)
    .filter((element) => !element.closest(`#${ROOT_ID}`));
  const activeRoots = new Set(roots);

  for (const [element, rootState] of state.rootStates) {
    if (activeRoots.has(element) && element.isConnected) {
      continue;
    }

    teardownSubtitleRoot(element, rootState, true);

    if (state.pinnedToken && element.contains(state.pinnedToken)) {
      closePinnedTooltip();
    }
  }

  for (const root of roots) {
    if (state.rootStates.has(root)) {
      syncSubtitleRoot(root);
      continue;
    }

    observeSubtitleRoot(root);
  }
}

function disconnectSubtitleRoots(restorePlainText: boolean): void {
  for (const [element, rootState] of state.rootStates) {
    teardownSubtitleRoot(element, rootState, restorePlainText);
  }

  state.rootStates.clear();
}

function teardownSubtitleRoot(
  element: HTMLElement,
  rootState: SubtitleRootState,
  restorePlainText: boolean
): void {
  rootState.observer.disconnect();
  element.removeAttribute(SUBTITLE_ROOT_ATTRIBUTE);

  if (restorePlainText && rootState.lastRenderedText) {
    element.textContent = rootState.lastRenderedText;
  }

  state.rootStates.delete(element);
}

function ensureDemoTrackBridge(): void {
  if (state.demoTrackCleanup) {
    return;
  }

  const video = document.querySelector<HTMLVideoElement>("#sample-video");
  const subtitle = document.querySelector<HTMLElement>("#subtitle");

  if (!video || !subtitle) {
    return;
  }

  const track = Array.from(video.textTracks).find((item) => {
    return item.kind === "subtitles" || item.kind === "captions";
  });

  if (!track) {
    return;
  }

  const syncFromTrack = () => {
    const cue = track.activeCues?.[0] ?? null;
    const cueText = getCueText(cue);
    subtitle.textContent = cueText;

    if (cue && track.cues) {
      const cues = Array.from(track.cues);
      const activeIndex = cues.indexOf(cue);
      const nextCueText = activeIndex >= 0 ? getCueText(cues[activeIndex + 1] ?? null) : "";

      if (nextCueText) {
        prefetchSubtitleLine(
          nextCueText,
          {
            sourceLanguage: state.sourceLanguage,
            targetLanguage: state.targetLanguage
          },
          { contextBefore: cueText }
        );
      }
    }
  };

  track.mode = "hidden";
  track.addEventListener("cuechange", syncFromTrack);
  syncFromTrack();

  state.demoTrackCleanup = () => {
    track.removeEventListener("cuechange", syncFromTrack);
  };
}

function disconnectDemoTrackBridge(): void {
  state.demoTrackCleanup?.();
  state.demoTrackCleanup = null;
}

async function initializeSettings(): Promise<void> {
  const settings = await readSettings();
  applySettings(settings);
  startPlatformWatcher();
}

function observeSubtitleRoot(element: HTMLElement): void {
  element.setAttribute(SUBTITLE_ROOT_ATTRIBUTE, "true");

  const rootState: SubtitleRootState = {
    isRendering: false,
    lastRenderedText: "",
    observer: new MutationObserver(() => {
      syncSubtitleRoot(element);
    }),
    translation: null,
    translationError: null,
    translationRequestId: 0
  };

  rootState.observer.observe(element, {
    childList: true,
    characterData: true,
    subtree: true
  });

  state.rootStates.set(element, rootState);
  syncSubtitleRoot(element);
}

function syncSubtitleRoot(element: HTMLElement): void {
  const rootState = state.rootStates.get(element);

  if (!rootState || rootState.isRendering) {
    return;
  }

  const text = element.textContent?.trim() ?? "";

  if (!text) {
    rootState.lastRenderedText = "";
    rootState.translation = null;
    rootState.translationError = null;

    if (state.pinnedToken && element.contains(state.pinnedToken)) {
      closePinnedTooltip();
    }

    return;
  }

  if (
    text === rootState.lastRenderedText &&
    (element.querySelector(`[${TOKEN_ATTRIBUTE}]`) || element.querySelector(`[${PLAIN_ATTRIBUTE}]`))
  ) {
    return;
  }

  const contextBefore = rootState.lastRenderedText || undefined;
  renderInteractiveSubtitle(element, text, rootState);
  requestSubtitleTranslation(element, text, rootState, contextBefore);
}

function renderInteractiveSubtitle(
  element: HTMLElement,
  text: string,
  rootState: SubtitleRootState
): void {
  rootState.isRendering = true;
  rootState.lastRenderedText = text;

  if (state.pinnedToken && element.contains(state.pinnedToken)) {
    closePinnedTooltip();
  }

  const segments = splitSegments(text);
  const fragment = document.createDocumentFragment();
  let hasInteractiveToken = false;

  for (let index = 0; index < segments.length; index += 1) {
    const segment = segments[index];

    if (!isWord(segment)) {
      fragment.append(document.createTextNode(segment));
      continue;
    }

    const match = findEntryAt(segments, index);

    hasInteractiveToken = true;

    if (match) {
      const label = segments.slice(index, match.endIndex + 1).join("");
      fragment.append(createToken(createDictionaryTooltipData(match.entry, rootState), label));
      index = match.endIndex;
      continue;
    }

    fragment.append(createToken(createLineTooltipData(segment, rootState), segment));
  }

  if (hasInteractiveToken) {
    element.replaceChildren(fragment);
  } else {
    const plainText = document.createElement("span");
    plainText.setAttribute(PLAIN_ATTRIBUTE, "true");
    plainText.textContent = text;
    element.replaceChildren(plainText);
  }

  rootState.isRendering = false;
}

function createToken(entry: TokenTooltipData, label: string): HTMLElement {
  const token = document.createElement("span");
  token.className = "sublingo-token";
  token.setAttribute(TOKEN_ATTRIBUTE, "true");
  token.setAttribute("role", "button");
  token.tabIndex = 0;
  token.textContent = label;

  token.addEventListener("mouseenter", (event) => showHoverTooltip(event, entry));
  token.addEventListener("mousemove", (event) => positionTooltipAtPointer(event));
  token.addEventListener("mouseleave", () => hideTooltip());
  token.addEventListener("focus", (event) => showHoverTooltip(event, entry));
  token.addEventListener("blur", () => hideTooltip());
  token.addEventListener("click", (event) => {
    event.stopPropagation();
    pinTooltip(token, entry);
  });
  token.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    event.preventDefault();
    pinTooltip(token, entry);
  });

  return token;
}

function showHoverTooltip(event: Event, entry: TokenTooltipData): void {
  if (state.pinnedToken) {
    return;
  }

  renderTooltip(entry, false);
  showTooltip();
  positionTooltipNearEvent(event);
}

function pinTooltip(token: HTMLElement, entry: TokenTooltipData): void {
  clearPinnedToken();
  state.pinnedToken = token;
  token.classList.add("sublingo-token-pinned");

  renderTooltip(entry, true);
  showTooltip();
  positionTooltipNearElement(token);

  const closeButton = state.tooltipElement?.querySelector("[data-close-tooltip]");
  const listenButton = state.tooltipElement?.querySelector("[data-pronunciation]");

  closeButton?.addEventListener("click", () => closePinnedTooltip());
  listenButton?.addEventListener("click", () => speak(entry.pronunciation));
}

function renderTooltip(entry: TokenTooltipData, pinned: boolean): void {
  if (!state.tooltipElement) {
    return;
  }

  if (entry.kind === "line") {
    renderLineTooltip(entry, pinned);
    return;
  }

  renderDictionaryTooltip(entry, pinned);
}

function renderDictionaryTooltip(entry: TokenTooltipData, pinned: boolean): void {
  if (!state.tooltipElement) {
    return;
  }

  state.tooltipElement.innerHTML = `
    <div class="tooltip-header">
      <p class="tooltip-title">${escapeHtml(entry.source)}</p>
      ${pinned ? '<button class="tooltip-close" type="button" data-close-tooltip aria-label="Close tooltip">x</button>' : ""}
    </div>
    <div class="tooltip-grid">
      <span class="tooltip-label">Translation</span>
      <p class="tooltip-value">${escapeHtml(entry.target)}</p>
      ${
        hasRomanization(entry.romanization)
          ? `<span class="tooltip-label">Romanization</span>
             <p class="tooltip-value">${escapeHtml(entry.romanization)}</p>`
          : ""
      }
      <span class="tooltip-label">Grammar</span>
      <p class="tooltip-value">${escapeHtml(entry.grammar)}</p>
    </div>
    ${
      isRedundantDefinition(entry.definition, entry.target)
        ? ""
        : `<p class="tooltip-body">${escapeHtml(entry.definition)}</p>`
    }
    ${
      pinned && entry.provider
        ? `<p class="tooltip-meta">${escapeHtml(entry.provider)} ${entry.isMock ? "(mock)" : ""}</p>`
        : ""
    }
    ${
      pinned
        ? `<button class="listen-button" type="button" data-pronunciation="${escapeHtml(entry.pronunciation)}">Listen</button>`
        : ""
    }
  `;

  state.tooltipElement.classList.toggle("pinned", pinned);
}

function renderLineTooltip(entry: TokenTooltipData, pinned: boolean): void {
  if (!state.tooltipElement) {
    return;
  }

  state.tooltipElement.innerHTML = `
    <div class="tooltip-header">
      <p class="tooltip-title">${escapeHtml(entry.source)} -> ${escapeHtml(entry.target)}</p>
      ${pinned ? '<button class="tooltip-close" type="button" data-close-tooltip aria-label="Close tooltip">x</button>' : ""}
    </div>
    ${
      pinned && entry.lineTranslation
        ? `<p class="tooltip-line">${escapeHtml(entry.lineTranslation)}</p>`
        : ""
    }
    ${
      pinned && entry.provider
        ? `<p class="tooltip-meta">${escapeHtml(entry.provider)} ${entry.isMock ? "(mock)" : ""}</p>`
        : ""
    }
    ${
      pinned && entry.target !== "Translation loading"
        ? `<button class="listen-button" type="button" data-pronunciation="${escapeHtml(entry.pronunciation)}">Listen</button>`
        : ""
    }
  `;

  state.tooltipElement.classList.toggle("pinned", pinned);
}

function createDictionaryTooltipData(
  entry: PreparedDictionaryEntry,
  rootState: SubtitleRootState
): TokenTooltipData {
  return {
    kind: "dictionary",
    source: entry.displaySource ?? entry.source,
    target: entry.target,
    romanization: entry.romanization,
    grammar: entry.grammar,
    definition: entry.definition,
    pronunciation: entry.pronunciation,
    lineTranslation: null,
    provider: rootState.translation?.provider ?? null,
    isMock: rootState.translation?.isMock ?? false
  };
}

function createLineTooltipData(token: string, rootState: SubtitleRootState): TokenTooltipData {
  const tokenTranslation = getTokenTranslation(token, rootState);

  return {
    kind: "line",
    source: token,
    target: tokenTranslation ?? "Translation loading",
    romanization: "-",
    grammar: "unknown",
    definition: rootState.translationError ?? "Translation loading.",
    pronunciation: tokenTranslation ?? token,
    lineTranslation: null,
    provider: rootState.translation?.provider ?? null,
    isMock: rootState.translation?.isMock ?? false
  };
}

function getTokenTranslation(token: string, rootState: SubtitleRootState): string | null {
  const key = normalizeTooltipToken(token);
  return rootState.translation?.tokenTranslations[key] ?? null;
}

function normalizeTooltipToken(value: string): string {
  return value
    .toLocaleLowerCase("fr-FR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/['’]/g, "")
    .trim();
}

async function requestSubtitleTranslation(
  element: HTMLElement,
  text: string,
  rootState: SubtitleRootState,
  contextBefore?: string
): Promise<void> {
  const requestId = rootState.translationRequestId + 1;
  rootState.translationRequestId = requestId;
  rootState.translation = null;
  rootState.translationError = null;

  try {
    const translation = await translateSubtitleLine(text, {
      sourceLanguage: state.sourceLanguage,
      targetLanguage: state.targetLanguage
    }, { contextBefore });

    if (rootState.translationRequestId !== requestId || rootState.lastRenderedText !== text) {
      return;
    }

    rootState.translation = translation;
    renderInteractiveSubtitle(element, text, rootState);
  } catch {
    if (rootState.translationRequestId !== requestId || rootState.lastRenderedText !== text) {
      return;
    }

    rootState.translationError = "Subtitle analysis backend unavailable.";
    renderInteractiveSubtitle(element, text, rootState);
  }
}

function showTooltip(): void {
  if (!state.tooltipElement) {
    return;
  }

  if (state.hideTooltipTimer !== null) {
    window.clearTimeout(state.hideTooltipTimer);
    state.hideTooltipTimer = null;
  }

  state.tooltipElement.hidden = false;
  requestAnimationFrame(() => {
    state.tooltipElement?.classList.add("visible");
  });
}

function hideTooltip(force = false): void {
  if (state.pinnedToken && !force) {
    return;
  }

  if (force) {
    clearPinnedToken();
  }

  state.tooltipElement?.classList.remove("visible");
  state.hideTooltipTimer = window.setTimeout(() => {
    if (!state.tooltipElement?.classList.contains("visible")) {
      state.tooltipElement?.classList.remove("pinned");

      if (state.tooltipElement) {
        state.tooltipElement.hidden = true;
      }
    }
  }, 120);
}

function closePinnedTooltip(): void {
  hideTooltip(true);
}

function clearPinnedToken(): void {
  if (!state.pinnedToken) {
    return;
  }

  state.pinnedToken.classList.remove("sublingo-token-pinned");
  state.pinnedToken = null;
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    closePinnedTooltip();
  }
}

function handleDocumentClick(event: MouseEvent): void {
  if (!state.pinnedToken || !state.tooltipElement) {
    return;
  }

  const tooltipRoot = state.tooltipElement.getRootNode();
  const target = event.target;

  if (target instanceof Node && (state.pinnedToken.contains(target) || tooltipRoot.contains(target))) {
    return;
  }

  closePinnedTooltip();
}

function positionTooltipAtPointer(event: Event): void {
  if (!(event instanceof MouseEvent) || state.pinnedToken) {
    return;
  }

  positionTooltip(event.clientX, event.clientY);
}

function positionTooltipNearEvent(event: Event): void {
  if (event instanceof MouseEvent) {
    positionTooltip(event.clientX, event.clientY);
    return;
  }

  if (event.currentTarget instanceof HTMLElement) {
    positionTooltipNearElement(event.currentTarget);
  }
}

function positionTooltip(clientX: number, clientY: number): void {
  if (!state.tooltipElement) {
    return;
  }

  const margin = 14;
  const rect = state.tooltipElement.getBoundingClientRect();
  const preferredLeft = clientX + margin;
  const preferredTop = clientY + margin;
  const left = Math.min(preferredLeft, window.innerWidth - rect.width - margin);
  const top = Math.min(preferredTop, window.innerHeight - rect.height - margin);

  state.tooltipElement.style.left = `${Math.max(margin, left)}px`;
  state.tooltipElement.style.top = `${Math.max(margin, top)}px`;
}

function positionTooltipNearElement(element: HTMLElement): void {
  if (!state.tooltipElement) {
    return;
  }

  const margin = 14;
  const gap = 12;
  const anchorRect = element.getBoundingClientRect();
  const tooltipRect = state.tooltipElement.getBoundingClientRect();
  const centeredLeft = anchorRect.left + anchorRect.width / 2 - tooltipRect.width / 2;
  const topAbove = anchorRect.top - tooltipRect.height - gap;
  const top = topAbove > margin ? topAbove : anchorRect.bottom + gap;
  const left = Math.min(centeredLeft, window.innerWidth - tooltipRect.width - margin);

  state.tooltipElement.style.left = `${Math.max(margin, left)}px`;
  state.tooltipElement.style.top = `${Math.max(margin, top)}px`;
}

function speak(text: string): void {
  if (!("speechSynthesis" in window)) {
    return;
  }

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function getCueText(cue: TextTrackCue | null): string {
  if (cue && "text" in cue && typeof cue.text === "string") {
    return cue.text;
  }

  return "";
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function handleStorageChanged(
  changes: Record<string, chrome.storage.StorageChange>,
  areaName: string
): void {
  if (areaName !== "sync" || !changes[SETTINGS_KEY]) {
    return;
  }

  applySettings(parseSettings(changes[SETTINGS_KEY].newValue));
}

function applySettings(settings: ExtensionSettings): void {
  const didEnabledChange = state.isEnabled !== settings.enabled;
  const didLanguageChange =
    state.sourceLanguage !== settings.sourceLanguage ||
    state.targetLanguage !== settings.targetLanguage;
  state.isEnabled = settings.enabled;
  state.sourceLanguage = settings.sourceLanguage;
  state.targetLanguage = settings.targetLanguage;

  if (didLanguageChange) {
    clearSubtitleTranslationCache();

    for (const [element, rootState] of state.rootStates) {
      rootState.lastRenderedText = "";
      rootState.translation = null;
      syncSubtitleRoot(element);
    }
  }

  if (didEnabledChange) {
    syncPlatform();
    return;
  }

  schedulePlatformSync();
}

async function readSettings(): Promise<ExtensionSettings> {
  const result = await chrome.storage.sync.get(SETTINGS_KEY);
  return parseSettings(result[SETTINGS_KEY]);
}

function parseSettings(value: unknown): ExtensionSettings {
  if (isRecord(value)) {
    return {
      enabled: typeof value.enabled === "boolean" ? value.enabled : true,
      sourceLanguage: typeof value.sourceLanguage === "string" ? value.sourceLanguage : "fr",
      targetLanguage: typeof value.targetLanguage === "string" ? value.targetLanguage : "en"
    };
  }

  return {
    enabled: true,
    sourceLanguage: "fr",
    targetLanguage: "en"
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

bootstrap();
