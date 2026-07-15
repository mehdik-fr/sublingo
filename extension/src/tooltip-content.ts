export function hasRomanization(value: string): boolean {
  const normalized = value.trim();
  return normalized.length > 0 && normalized !== "-";
}
