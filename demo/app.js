const videoElement = document.querySelector("#sample-video");
const subtitleTrackElement = document.querySelector("#subtitle-track");
const subtitleElement = document.querySelector("#subtitle");
const contextNoteElement = document.querySelector("#context-note");
const replayButton = document.querySelector("#replay-video");
const nextCueButton = document.querySelector("#next-cue");

let isSubtitleTrackReady = false;

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

  if (!activeCue) {
    subtitleElement.textContent = "";
    contextNoteElement.textContent = "Waiting for the next subtitle cue.";
    return;
  }

  subtitleElement.textContent = activeCue.text;
  contextNoteElement.textContent = `Demo cue: ${formatTime(activeCue.startTime)} -> ${formatTime(activeCue.endTime)}`;
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

function playVideo() {
  videoElement.play().catch(() => {
    contextNoteElement.textContent = "Press the native video play button to start playback.";
  });
}

replayButton.addEventListener("click", () => {
  videoElement.currentTime = 0;
  playVideo();
});

nextCueButton.addEventListener("click", jumpToNextCue);

subtitleTrackElement.addEventListener("load", setupSubtitleTrack);
subtitleTrackElement.addEventListener("error", () => {
  contextNoteElement.textContent = "The subtitle file could not be loaded.";
});

videoElement.addEventListener("loadedmetadata", () => {
  subtitleTrackElement.track.mode = "hidden";
  contextNoteElement.textContent = "This page only shows plain subtitles. The extension adds interactivity.";

  if (subtitleTrackElement.readyState === HTMLTrackElement.LOADED) {
    setupSubtitleTrack();
  }
});

videoElement.addEventListener("ended", () => {
  contextNoteElement.textContent = "Video ended. Replay to test the extension again.";
});
