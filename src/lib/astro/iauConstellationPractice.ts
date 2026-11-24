import { getConstellation } from "./catalog";

export type IauPracticeMode = "easy" | "advanced";

export interface IauPracticeQuestion {
  id: string;
  questionImageUrl: string;
  annotatedImageUrl: string;
  answer: string;
  constellationId: string;
  abbreviation: string;
}

/**
 * IAU constellation IDs that have all required assets present:
 * - easy: /iau-constellations/text-removed/{abbr}.webp
 * - advanced: /iau-constellations/processed/{abbr}_processed.webp
 * - annotated: /iau-constellations/annotated-webp/{abbr}.webp
 *
 * Derived from the actual public/iau-constellations asset directories.
 * Serpens (ser) is currently excluded because it has no matching assets in these directories.
 */
export const IAU_PRACTICE_CONSTELLATION_IDS = [
  "and", "ant", "aps", "aql", "aqr", "ara", "ari", "aur", "boo", "cae",
  "cam", "cap", "car", "cas", "cen", "cep", "cet", "cha", "cir", "cma",
  "cmi", "cnc", "col", "com", "cra", "crb", "crt", "cru", "crv", "cvn",
  "cyg", "del", "dor", "dra", "equ", "eri", "for", "gem", "gru", "her",
  "hor", "hya", "hyi", "ind", "lac", "leo", "lep", "lib", "lmi", "lup",
  "lyn", "lyr", "men", "mic", "mon", "mus", "nor", "oct", "oph", "ori",
  "pav", "peg", "per", "phe", "pic", "psa", "psc", "pup", "pyx", "ret",
  "scl", "sco", "sct", "sex", "sge", "sgr", "tau", "tel", "tra", "tri",
  "tuc", "uma", "umi", "vel", "vir", "vol", "vul",
] as const;

export type IauPracticeConstellationId = (typeof IAU_PRACTICE_CONSTELLATION_IDS)[number];

const IAU_PRACTICE_ID_SET = new Set<string>(IAU_PRACTICE_CONSTELLATION_IDS);

export const IAU_PRACTICE_MODE_CONFIG: Record<
  IauPracticeMode,
  { label: string; blurb: string; directory: string }
> = {
  easy: {
    label: "Easy",
    blurb: "Constellation lines are present.",
    directory: "/iau-constellations/text-removed",
  },
  advanced: {
    label: "Advanced",
    blurb: "No constellation lines.",
    directory: "/iau-constellations/processed",
  },
};

export function isIauPracticeConstellationId(id: string): id is IauPracticeConstellationId {
  return IAU_PRACTICE_ID_SET.has(id.toLowerCase());
}

export function getIauPracticeQuestionImageUrl(id: string, mode: IauPracticeMode): string {
  const abbr = id.toLowerCase();
  if (mode === "easy") return `/iau-constellations/text-removed/${abbr}.webp`;
  return `/iau-constellations/processed/${abbr}_processed.webp`;
}

export function getIauAnnotatedImageUrl(id: string): string {
  return `/iau-constellations/annotated-webp/${id.toLowerCase()}.webp`;
}

export function normalizeIauAnswer(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[\u2019']/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function getAcceptedIauAnswers(id: string): string[] {
  const c = getConstellation(id);
  if (!c) return [];
  const answers = new Set<string>();
  answers.add(normalizeIauAnswer(c.name));
  // Abbreviation is an explicit official identifier; accept it as a clear alias.
  answers.add(normalizeIauAnswer(c.abbreviation));
  return [...answers];
}

export function isCorrectIauAnswer(input: string, id: string): boolean {
  const normalized = normalizeIauAnswer(input);
  if (!normalized) return false;
  return getAcceptedIauAnswers(id).includes(normalized);
}

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j]!, a[i]!];
  }
  return a;
}

export function buildIauPracticeQuestions(mode: IauPracticeMode): IauPracticeQuestion[] {
  return shuffle(IAU_PRACTICE_CONSTELLATION_IDS.map((id) => {
    const c = getConstellation(id);
    if (!c) return null;
    return {
      id: c.id,
      constellationId: c.id,
      abbreviation: c.abbreviation,
      answer: c.name,
      questionImageUrl: getIauPracticeQuestionImageUrl(c.id, mode),
      annotatedImageUrl: getIauAnnotatedImageUrl(c.id),
    };
  }).filter((q): q is IauPracticeQuestion => q !== null));
}

export function preloadImage(url: string): Promise<boolean> {
  return new Promise<boolean>((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img.naturalWidth > 0);
    img.onerror = () => resolve(false);
    img.src = url;
  });
}
