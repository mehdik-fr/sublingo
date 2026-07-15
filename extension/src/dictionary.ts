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
    target: "flower",
    romanization: "-",
    grammar: "noun",
    definition: "A flower.",
    pronunciation: "flower"
  },
  {
    source: "s'ouvre",
    displaySource: "s'ouvrir",
    target: "opens",
    romanization: "-",
    grammar: "verb",
    definition: "To open. For flowers, it can also mean to bloom.",
    pronunciation: "opens"
  },
  {
    source: "regardez",
    target: "look",
    romanization: "-",
    grammar: "verb",
    definition: "To see, watch, or look at.",
    pronunciation: "look"
  },
  {
    source: "de plus pres",
    displaySource: "de plus pres",
    target: "more closely",
    romanization: "-",
    grammar: "expression",
    definition: "From closer up, or more closely.",
    pronunciation: "more closely"
  },
  {
    source: "couleurs",
    target: "colors",
    romanization: "-",
    grammar: "noun",
    definition: "Colors.",
    pronunciation: "colors"
  },
  {
    source: "lentement",
    target: "slowly",
    romanization: "-",
    grammar: "adverb",
    definition: "Slowly.",
    pronunciation: "slowly"
  }
];
