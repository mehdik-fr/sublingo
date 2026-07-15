import type { SubtitleSegmentAnalysis } from "./subtitle-analysis-mapper";

export type SubtitleRenderPart = {
  text: string;
  segment: SubtitleSegmentAnalysis | null;
};

type MatchedRange = {
  start: number;
  end: number;
  segment: SubtitleSegmentAnalysis;
};

export function buildSubtitleRenderParts(
  sourceText: string,
  segments: SubtitleSegmentAnalysis[]
): SubtitleRenderPart[] {
  const occupied = new Array<boolean>(sourceText.length).fill(false);
  const rankedSegments = segments
    .filter(isInteractiveSegment)
    .map((segment, index) => ({ segment, index }))
    .sort((left, right) => {
      const kindDifference = kindPriority(right.segment) - kindPriority(left.segment);

      if (kindDifference !== 0) {
        return kindDifference;
      }

      const lengthDifference = right.segment.surface.length - left.segment.surface.length;
      return lengthDifference !== 0 ? lengthDifference : left.index - right.index;
    });
  const matchedRanges: MatchedRange[] = [];

  for (const { segment } of rankedSegments) {
    const start = findAvailableOccurrence(sourceText, segment.surface, occupied);

    if (start < 0) {
      continue;
    }

    const end = start + segment.surface.length;

    for (let index = start; index < end; index += 1) {
      occupied[index] = true;
    }

    matchedRanges.push({ start, end, segment });
  }

  matchedRanges.sort((left, right) => left.start - right.start);

  if (matchedRanges.length === 0) {
    return [{ text: sourceText, segment: null }];
  }

  const parts: SubtitleRenderPart[] = [];
  let cursor = 0;

  for (const match of matchedRanges) {
    if (match.start > cursor) {
      parts.push({ text: sourceText.slice(cursor, match.start), segment: null });
    }

    parts.push({ text: sourceText.slice(match.start, match.end), segment: match.segment });
    cursor = match.end;
  }

  if (cursor < sourceText.length) {
    parts.push({ text: sourceText.slice(cursor), segment: null });
  }

  return parts;
}

function isInteractiveSegment(segment: SubtitleSegmentAnalysis): boolean {
  return (
    (segment.kind === "word" || segment.kind === "expression") &&
    segment.surface.length > 0 &&
    segment.translations.length > 0
  );
}

function kindPriority(segment: SubtitleSegmentAnalysis): number {
  return segment.kind === "expression" ? 2 : 1;
}

function findAvailableOccurrence(sourceText: string, surface: string, occupied: boolean[]): number {
  let searchFrom = 0;

  while (searchFrom <= sourceText.length - surface.length) {
    const start = sourceText.indexOf(surface, searchFrom);

    if (start < 0) {
      return -1;
    }

    const end = start + surface.length;
    const hasValidBoundaries =
      (!isWordCharacter(surface[0]) || !isWordCharacter(sourceText[start - 1])) &&
      (!isWordCharacter(surface[surface.length - 1]) || !isWordCharacter(sourceText[end]));
    const isAvailable = occupied.slice(start, end).every((value) => !value);

    if (hasValidBoundaries && isAvailable) {
      return start;
    }

    searchFrom = start + 1;
  }

  return -1;
}

function isWordCharacter(value: string | undefined): boolean {
  return value !== undefined && /[\p{L}\p{M}\p{N}]/u.test(value);
}
