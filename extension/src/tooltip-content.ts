export function hasRomanization(value: string): boolean {
  const normalized = value.trim();
  return normalized.length > 0 && normalized !== "-";
}

export function isRedundantDefinition(definition: string, translation: string): boolean {
  const normalizedDefinition = normalizeMeaning(definition);
  const normalizedTranslation = normalizeMeaning(translation);

  return (
    normalizedDefinition === normalizedTranslation ||
    normalizedDefinition === `a ${normalizedTranslation}` ||
    normalizedDefinition === `an ${normalizedTranslation}` ||
    normalizedDefinition === `the ${normalizedTranslation}`
  );
}

function normalizeMeaning(value: string): string {
  return value
    .toLocaleLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}
