import { dictionary, type PreparedDictionaryEntry } from "./dictionary";

export type DictionaryMatch = {
  entry: PreparedDictionaryEntry;
  endIndex: number;
};

export const preparedDictionary: PreparedDictionaryEntry[] = dictionary
  .map((entry) => ({
    ...entry,
    key: normalize(entry.source),
    wordCount: normalize(entry.source).split(" ").length
  }))
  .sort((left, right) => right.wordCount - left.wordCount);

export function splitSegments(text: string): string[] {
  return text.match(/[\p{L}\p{M}'-]+|[^\p{L}\p{M}'-]+/gu) ?? [];
}

export function isWord(segment: string): boolean {
  return /[\p{L}\p{M}]/u.test(segment);
}

export function findEntryAt(segments: string[], startIndex: number): DictionaryMatch | null {
  for (const entry of preparedDictionary) {
    const indexes = getWordIndexes(segments, startIndex, entry.wordCount);

    if (indexes.length !== entry.wordCount) {
      continue;
    }

    const candidate = indexes.map((index) => normalize(segments[index])).join(" ");

    if (candidate === entry.key) {
      return {
        entry,
        endIndex: indexes[indexes.length - 1]
      };
    }
  }

  return null;
}

export function normalize(value: string): string {
  return value
    .toLocaleLowerCase("fr-FR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/['’]/g, "'")
    .trim();
}

function getWordIndexes(segments: string[], startIndex: number, count: number): number[] {
  const indexes: number[] = [];

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
