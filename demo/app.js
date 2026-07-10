const dictionary = [
  {
    source: "fleur",
    target: "꽃",
    romanization: "kkot",
    grammar: "noun",
    definition: "A flower.",
    pronunciation: "꽃",
  },
  {
    source: "s'ouvre",
    displaySource: "s'ouvrir",
    target: "피다 / 열리다",
    romanization: "pida / yeollida",
    grammar: "verb",
    definition: "To open or bloom. For flowers, Korean often uses 피다.",
    pronunciation: "피다",
  },
  {
    source: "regardez",
    target: "보다",
    romanization: "boda",
    grammar: "verb",
    definition: "To see, watch, or look at.",
    pronunciation: "보다",
  },
  {
    source: "de plus pres",
    displaySource: "de plus près",
    target: "더 가까이",
    romanization: "deo gakkai",
    grammar: "expression",
    definition: "From closer up, or more closely.",
    pronunciation: "더 가까이",
  },
  {
    source: "couleurs",
    target: "색",
    romanization: "saek",
    grammar: "noun",
    definition: "Colors.",
    pronunciation: "색",
  },
  {
    source: "lentement",
    target: "천천히",
    romanization: "cheoncheonhi",
    grammar: "adverb",
    definition: "Slowly.",
    pronunciation: "천천히",
  },
];

const preparedDictionary = dictionary
  .map((entry) => ({
    ...entry,
    key: normalize(entry.source),
    wordCount: normalize(entry.source).split(" ").length,
  }))
  .sort((a, b) => b.wordCount - a.wordCount);

const videoElement = document.querySelector("#sample-video");
const subtitleTrackElement = document.querySelector("#subtitle-track");
const subtitleElement = document.querySelector("#subtitle");
const contextNoteElement = document.querySelector("#context-note");
const tooltipElement = document.querySelector("#tooltip");
const replayButton = document.querySelector("#replay-video");
const nextCueButton = document.querySelector("#next-cue");

let isSubtitleTrackReady = false;
let pinnedTooltipToken = null;
let hideTooltipTimer = null;

function normalize(value) {
  return value
    .toLocaleLowerCase("fr-FR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[’]/g, "'")
    .trim();
}

function splitSegments(text) {
  return text.match(/[\p{L}\p{M}'-]+|[^\p{L}\p{M}'-]+/gu) ?? [];
}

function isWord(segment) {
  return /[\p{L}\p{M}]/u.test(segment);
}

function getWordIndexes(segments, startIndex, count) {
  const indexes = [];

  for (let index = startIndex; index < segments.length; index += 1) {
    if (isWord(segments[index])) {
      indexes.push(index);
    }

    if (indexes.length === count) {
      return indexes;
    }
  }

  return [];
}

function findEntryAt(segments, startIndex) {
  for (const entry of preparedDictionary) {
    const indexes = getWordIndexes(segments, startIndex, entry.wordCount);

    if (indexes.length !== entry.wordCount) {
      continue;
    }

    const candidate = indexes.map((index) => normalize(segments[index])).join(" ");

    if (candidate === entry.key) {
      return {
        entry,
        endIndex: indexes[indexes.length - 1],
      };
    }
  }

  return null;
}

function renderSubtitle(text) {
  const segments = splitSegments(text);
  const fragment = document.createDocumentFragment();

  for (let index = 0; index < segments.length; index += 1) {
    const segment = segments[index];

    if (!isWord(segment)) {
      fragment.append(document.createTextNode(segment));
      continue;
    }

    const match = findEntryAt(segments, index);

    if (!match) {
      fragment.append(document.createTextNode(segment));
      continue;
    }

    const token = document.createElement("span");
    token.className = `token ${match.entry.wordCount > 1 ? "expression" : ""}`.trim();
    token.setAttribute("role", "button");
    token.tabIndex = 0;
    token.textContent = segments.slice(index, match.endIndex + 1).join("");

    token.addEventListener("mouseenter", (event) => showHoverTooltip(event, match.entry));
    token.addEventListener("mousemove", (event) => positionTooltip(event));
    token.addEventListener("mouseleave", hideTooltip);
    token.addEventListener("focus", (event) => showHoverTooltip(event, match.entry));
    token.addEventListener("blur", hideTooltip);
    token.addEventListener("click", (event) => {
      event.stopPropagation();
      pinTooltip(token, match.entry);
    });
    token.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }

      event.preventDefault();
      pinTooltip(token, match.entry);
    });

    fragment.append(token);
    index = match.endIndex;
  }

  subtitleElement.replaceChildren(fragment);
}

function showHoverTooltip(event, entry) {
  if (pinnedTooltipToken) {
    return;
  }

  renderTooltip(entry, { pinned: false });
  showTooltipPanel();
  positionTooltipNearEventTarget(event);
}

function pinTooltip(token, entry) {
  clearPinnedTooltipToken();
  pinnedTooltipToken = token;
  pinnedTooltipToken.classList.add("pinned-token");

  renderTooltip(entry, { pinned: true });
  showTooltipPanel();
  positionTooltipNearElement(token);

  tooltipElement.querySelector("[data-close-tooltip]").addEventListener("click", closePinnedTooltip);
  tooltipElement.querySelector("[data-pronunciation]").addEventListener("click", () => {
    speak(entry.pronunciation);
  });
}

function renderTooltip(entry, { pinned }) {
  tooltipElement.innerHTML = `
    <div class="tooltip-header">
      <h2>${escapeHtml(entry.displaySource ?? entry.source)} -> ${escapeHtml(entry.target)}</h2>
      ${
        pinned
          ? '<button class="tooltip-close" type="button" data-close-tooltip aria-label="Close tooltip">x</button>'
          : ""
      }
    </div>
    <dl>
      <dt>Hangul</dt><dd>${escapeHtml(entry.target)}</dd>
      <dt>Romanization</dt><dd>${escapeHtml(entry.romanization)}</dd>
      <dt>Grammar</dt><dd>${escapeHtml(entry.grammar)}</dd>
    </dl>
    <p>${escapeHtml(entry.definition)}</p>
    ${
      pinned
        ? `<button class="listen-button" type="button" data-pronunciation="${escapeHtml(entry.pronunciation)}">Listen</button>`
        : ""
    }
  `;

  tooltipElement.classList.toggle("pinned", pinned);
}

function showTooltipPanel() {
  window.clearTimeout(hideTooltipTimer);
  tooltipElement.hidden = false;
  requestAnimationFrame(() => tooltipElement.classList.add("visible"));
}

function positionTooltip(event) {
  if (pinnedTooltipToken) {
    return;
  }

  positionTooltipAt(event.clientX, event.clientY);
}

function positionTooltipNearEventTarget(event) {
  if (Number.isFinite(event.clientX) && Number.isFinite(event.clientY)) {
    positionTooltipAt(event.clientX, event.clientY);
    return;
  }

  positionTooltipNearElement(event.currentTarget);
}

function positionTooltipAt(clientX, clientY) {
  const margin = 14;
  const rect = tooltipElement.getBoundingClientRect();
  const preferredLeft = clientX + margin;
  const preferredTop = clientY + margin;
  const left = Math.min(preferredLeft, window.innerWidth - rect.width - margin);
  const top = Math.min(preferredTop, window.innerHeight - rect.height - margin);

  tooltipElement.style.left = `${Math.max(margin, left)}px`;
  tooltipElement.style.top = `${Math.max(margin, top)}px`;
}

function positionTooltipNearElement(element) {
  const margin = 14;
  const gap = 12;
  const anchorRect = element.getBoundingClientRect();
  const tooltipRect = tooltipElement.getBoundingClientRect();
  const centeredLeft = anchorRect.left + anchorRect.width / 2 - tooltipRect.width / 2;
  const topAbove = anchorRect.top - tooltipRect.height - gap;
  const top = topAbove > margin ? topAbove : anchorRect.bottom + gap;
  const left = Math.min(centeredLeft, window.innerWidth - tooltipRect.width - margin);

  tooltipElement.style.left = `${Math.max(margin, left)}px`;
  tooltipElement.style.top = `${Math.max(margin, top)}px`;
}

function hideTooltip({ force = false } = {}) {
  if (pinnedTooltipToken && !force) {
    return;
  }

  if (force) {
    clearPinnedTooltipToken();
  }

  tooltipElement.classList.remove("visible");
  hideTooltipTimer = window.setTimeout(() => {
    if (!tooltipElement.classList.contains("visible")) {
      tooltipElement.hidden = true;
      tooltipElement.classList.remove("pinned");
    }
  }, 120);
}

function closePinnedTooltip() {
  hideTooltip({ force: true });
}

function clearPinnedTooltipToken() {
  if (!pinnedTooltipToken) {
    return;
  }

  pinnedTooltipToken.classList.remove("pinned-token");
  pinnedTooltipToken = null;
}

function speak(text) {
  if (!("speechSynthesis" in window)) {
    return;
  }

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "ko-KR";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function setupSubtitleTrack() {
  if (isSubtitleTrackReady) {
    return;
  }

  const track = subtitleTrackElement.track;

  isSubtitleTrackReady = true;
  track.mode = "hidden";
  track.addEventListener("cuechange", showActiveCue);
  showActiveCue();
}

function showActiveCue() {
  const activeCue = subtitleTrackElement.track.activeCues?.[0];

  hideTooltip({ force: true });

  if (!activeCue) {
    subtitleElement.replaceChildren();
    contextNoteElement.textContent = "Waiting for the next WebVTT subtitle cue.";
    return;
  }

  renderSubtitle(activeCue.text);
  contextNoteElement.textContent = `WebVTT cue: ${formatTime(activeCue.startTime)} -> ${formatTime(activeCue.endTime)}`;
}

function jumpToNextCue() {
  const cues = Array.from(subtitleTrackElement.track.cues ?? []);
  const nextCue = cues.find((cue) => cue.startTime > videoElement.currentTime + 0.1) ?? cues[0];

  if (!nextCue) {
    return;
  }

  videoElement.currentTime = nextCue.startTime + 0.05;
  playVideo();
}

function formatTime(seconds) {
  return `${seconds.toFixed(1)}s`;
}

replayButton.addEventListener("click", () => {
  videoElement.currentTime = 0;
  playVideo();
});

nextCueButton.addEventListener("click", jumpToNextCue);
tooltipElement.addEventListener("click", (event) => event.stopPropagation());
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closePinnedTooltip();
  }
});

subtitleTrackElement.addEventListener("load", setupSubtitleTrack);
subtitleTrackElement.addEventListener("error", () => {
  contextNoteElement.textContent = "The WebVTT subtitle file could not be loaded.";
});

videoElement.addEventListener("loadedmetadata", () => {
  subtitleTrackElement.track.mode = "hidden";
  contextNoteElement.textContent = "Press play to test WebVTT subtitles on a real video.";

  if (subtitleTrackElement.readyState === HTMLTrackElement.LOADED) {
    setupSubtitleTrack();
  }
});

videoElement.addEventListener("ended", () => {
  contextNoteElement.textContent = "Video ended. Replay to test the subtitle interaction again.";
});

function playVideo() {
  videoElement.play().catch(() => {
    contextNoteElement.textContent = "Press the native video play button to start playback.";
  });
}
