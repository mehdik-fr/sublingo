export type DictionaryEntry = {
  source: string;
  displaySource?: string;
  target: string;
  romanization: string;
  grammar: string;
  definition: string;
  pronunciation: string;
};

export type PreparedDictionaryEntry = DictionaryEntry & {
  key: string;
  wordCount: number;
};

export const dictionary: DictionaryEntry[] = [
  {
    source: "fleur",
    target: "kkoch",
    romanization: "kkoch",
    grammar: "noun",
    definition: "A flower.",
    pronunciation: "kkoch"
  },
  {
    source: "s'ouvre",
    displaySource: "s'ouvrir",
    target: "pida",
    romanization: "pida",
    grammar: "verb",
    definition: "To open or bloom. For flowers, Korean often uses pida.",
    pronunciation: "pida"
  },
  {
    source: "regardez",
    target: "boda",
    romanization: "boda",
    grammar: "verb",
    definition: "To see, watch, or look at.",
    pronunciation: "boda"
  },
  {
    source: "de plus pres",
    displaySource: "de plus pres",
    target: "deo gakkai",
    romanization: "deo gakkai",
    grammar: "expression",
    definition: "From closer up, or more closely.",
    pronunciation: "deo gakkai"
  },
  {
    source: "couleurs",
    target: "saek",
    romanization: "saek",
    grammar: "noun",
    definition: "Colors.",
    pronunciation: "saek"
  },
  {
    source: "lentement",
    target: "cheoncheonhi",
    romanization: "cheoncheonhi",
    grammar: "adverb",
    definition: "Slowly.",
    pronunciation: "cheoncheonhi"
  }
];
