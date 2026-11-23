import { angularSeparation, constellations, figureStarsOf, getConstellation } from "./catalog";
import { fitConstellation } from "./fov";
import { QuestionType } from "./types";
import type { Constellation, Difficulty, Question, SkyState } from "./types";

/** Difficulty only changes the *challenge before answering*, never the reveal. */
export const DIFFICULTY_PROFILE: Record<
  Difficulty,
  {
    magnitudeLimit: number;
    showLines: boolean;
    showBoundary: boolean;
    showGrid: boolean;
    labelMode: SkyState["labelMode"];
    maxRotation: number;
    fovScale: number;
  }
> = {
  beginner: {
    magnitudeLimit: 5.3,
    showLines: true,
    showBoundary: true,
    showGrid: true,
    labelMode: "none",
    maxRotation: 0,
    fovScale: 1,
  },
  intermediate: {
    magnitudeLimit: 5.6,
    showLines: false,
    showBoundary: true,
    showGrid: true,
    labelMode: "none",
    maxRotation: 25,
    fovScale: 1.25,
  },
  advanced: {
    magnitudeLimit: 6.5,
    showLines: false,
    showBoundary: true,
    showGrid: false,
    labelMode: "none",
    maxRotation: 60,
    fovScale: 1.6,
  },
};

function rng(): number {
  return Math.random();
}

function pick<T>(arr: T[]): T {
  return arr[Math.floor(rng() * arr.length)] as T;
}

/** Geometric "size" of a figure in degrees, used to pick similar-scale distractors. */
function figureSpan(c: Constellation): number {
  const stars = figureStarsOf(c);
  let max = 0;
  for (const s of stars) {
    const sep = angularSeparation(c.centerRa, c.centerDec, s.ra, s.dec);
    if (sep > max) max = sep;
  }
  return max * 2;
}

const spanCache = new Map<string, number>();
function spanOf(c: Constellation): number {
  let v = spanCache.get(c.id);
  if (v === undefined) {
    v = figureSpan(c);
    spanCache.set(c.id, v);
  }
  return v;
}

/**
 * Plausible distractors: same sky neighbourhood, comparable angular size and a
 * similar number of figure stars — never four random constellations.
 */
export function distractorsFor(target: Constellation, count = 3): Constellation[] {
  const targetSpan = spanOf(target);
  const scored = constellations
    .filter((c) => c.id !== target.id)
    .map((c) => {
      const dist = angularSeparation(target.centerRa, target.centerDec, c.centerRa, c.centerDec);
      const sizeRatio = Math.abs(Math.log((spanOf(c) + 1) / (targetSpan + 1)));
      const shapeDiff = Math.abs(c.lineData.length - target.lineData.length) / 12;
      const zodiacBonus = c.isEcliptic === target.isEcliptic ? -0.4 : 0;
      return { c, score: dist / 45 + sizeRatio * 1.5 + shapeDiff + zodiacBonus + rng() * 0.6 };
    })
    .sort((a, b) => a.score - b.score);
  return scored
    .slice(0, Math.max(count, 8))
    .sort(() => rng() - 0.5)
    .slice(0, count)
    .map((s) => s.c);
}

export function buildSkyState(c: Constellation, difficulty: Difficulty): SkyState {
  const profile = DIFFICULTY_PROFILE[difficulty];
  const view = fitConstellation(c);
  const rotation = profile.maxRotation ? (rng() * 2 - 1) * profile.maxRotation : 0;
  return {
    centerRa: view.ra,
    centerDec: view.dec,
    fovDeg: Math.min(150, view.fov * profile.fovScale),
    rotation,
    magnitudeLimit: profile.magnitudeLimit,
    showLines: profile.showLines,
    showBoundary: profile.showBoundary,
    showGrid: profile.showGrid,
    labelMode: profile.labelMode,
  };
}

let seq = 0;

export function generateConstellationQuestion(difficulty: Difficulty, pool?: string[]): Question {
  const candidates = pool?.length
    ? (pool.map(getConstellation).filter(Boolean) as Constellation[])
    : constellations;
  const target = pick(candidates.length ? candidates : constellations);
  const choices = [target, ...distractorsFor(target)]
    .sort(() => rng() - 0.5)
    .map((c) => ({ id: c.id, label: c.name }));
  seq += 1;
  return {
    id: `q${Date.now()}-${seq}`,
    type: QuestionType.IDENTIFY_CONSTELLATION,
    target: target.id,
    difficulty,
    skyState: buildSkyState(target, difficulty),
    choices,
    correctAnswer: target.id,
  };
}

export function generateIAUImageQuestion(pool?: string[]): Question {
  const candidates = pool?.length
    ? (pool.map(getConstellation).filter(Boolean) as Constellation[])
    : constellations;
  const target = pick(candidates.length ? candidates : constellations);
  const choices = [target, ...distractorsFor(target)]
    .sort(() => rng() - 0.5)
    .map((c) => ({ id: c.id, label: c.name }));
  seq += 1;
  return {
    id: `q${Date.now()}-${seq}`,
    type: QuestionType.IDENTIFY_CONSTELLATION_FROM_IMAGE,
    target: target.id,
    difficulty: "intermediate", // Fixed difficulty for image mode
    skyState: buildSkyState(target, "beginner"), // Not used, but included for compatibility
    choices,
    correctAnswer: target.id,
  };
}

/** Single entry point so future modes plug in without touching the practice UI. */
export function generateQuestion(
  type: QuestionType,
  difficulty: Difficulty,
  pool?: string[],
): Question {
  switch (type) {
    case QuestionType.IDENTIFY_CONSTELLATION:
      return generateConstellationQuestion(difficulty, pool);
    case QuestionType.IDENTIFY_CONSTELLATION_FROM_IMAGE:
      return generateIAUImageQuestion(pool);
    case QuestionType.IDENTIFY_CONSTELLATION_FROM_REAL_SKY_IMAGE:
      return generateRealSkyQuestion(pool);
    default:
      throw new Error(`Question type ${type} is not implemented yet`);
  }
}

/**
 * Generate a Real-Sky Challenge question using only constellations that have
 * an available unannotated photograph. All choices (correct + distractors)
 * are drawn from the eligible pool so no option shows a missing image.
 */
export function generateRealSkyQuestion(pool?: string[]): Question {
  const candidates = pool?.length
    ? (pool.map(getConstellation).filter(Boolean) as Constellation[])
    : constellations;

  if (candidates.length === 0) {
    throw new Error("No eligible constellations for Real-Sky Challenge");
  }

  const target = candidates[Math.floor(Math.random() * candidates.length)]!;

  // Pick 3 distinct distractors from the eligible pool (excluding target)
  const others = candidates.filter((c) => c.id !== target.id);
  const shuffled = [...others].sort(() => Math.random() - 0.5);
  const distractors = shuffled.slice(0, 3);

  const choices = [target, ...distractors]
    .sort(() => Math.random() - 0.5)
    .map((c) => ({ id: c.id, label: c.name }));

  return {
    id: `q-rs-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    type: QuestionType.IDENTIFY_CONSTELLATION_FROM_REAL_SKY_IMAGE,
    target: target.id,
    difficulty: "beginner", // Real-sky uses Easy/Advanced, mapped externally
    skyState: buildSkyState(target, "beginner"),
    choices,
    correctAnswer: target.id,
  };
}
