/**
 * Centralized asset resolver for NOIRLab real-sky constellation photographs.
 *
 * Images live under:
 *
 *   public/images/constellations/real-sky/unannotated/{abbreviation}.{ext}
 *   public/images/constellations/real-sky/annotated/{abbreviation}.{ext}
 *
 * Filenames use the official three-letter IAU abbreviation (lowercase) from the
 * constellation catalogue, e.g. `and.webp` for Andromeda. A constellation may
 * have several photographs, distinguished by a numeric suffix:
 *   and.webp, and-02.webp, and-03.webp, ...
 *
 * Supported extensions: .webp, .jpg, .jpeg, .png (probed in that order).
 *
 * Components should import `resolveConstellationImageUrl` / `resolveConstellationImage`
 * rather than hardcoding paths. Never hardcode an extension: the on-disk format
 * is WebP, but callers must not assume any single extension.
 */

import { constellations } from "./catalog";

const IMAGE_ROOT = "/images/constellations/real-sky";
const EXTENSIONS = [".webp", ".jpg", ".jpeg", ".png"] as const;

type ImageVariant = "unannotated" | "annotated";

// Highest numeric suffix to probe for multi-image constellations.
const MAX_IMAGE_SUFFIX = 20;

const availabilityCache = new Map<string, Promise<string | null>>();

function cacheKey(variant: ImageVariant, abbreviation: string): string {
  return `${variant}:${abbreviation.toLowerCase()}`;
}

/** Build every candidate URL for a variant, base image first, then -02, -03, … */
function candidateUrls(variant: ImageVariant, abbreviation: string): string[] {
  const base = abbreviation.toLowerCase();
  const urls: string[] = [];
  for (const ext of EXTENSIONS) {
    urls.push(`${IMAGE_ROOT}/${variant}/${base}${ext}`);
  }
  for (let n = 2; n <= MAX_IMAGE_SUFFIX; n += 1) {
    const suffix = `-${String(n).padStart(2, "0")}`;
    for (const ext of EXTENSIONS) {
      urls.push(`${IMAGE_ROOT}/${variant}/${base}${suffix}${ext}`);
    }
  }
  return urls;
}

/**
 * Probe whether a single image file exists by attempting to load it.
 * Cached per URL so repeated probes for the same file are cheap.
 */
function probeImageUrl(url: string): Promise<boolean> {
  const cached = availabilityCache.get(url);
  if (cached) {
    return cached.then((u) => u !== null);
  }

  const load = new Promise<boolean>((resolve) => {
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = url;
  });

  availabilityCache.set(
    url,
    load.then((ok) => (ok ? url : null)),
  );
  return load;
}

/**
 * Resolve the URL for the first available photograph of a constellation variant.
 * Probes the base image (`and.webp`, `and.jpg`, …) before any numbered variants
 * (`and-02.webp`, …). Returns `null` when nothing is available.
 */
export async function resolveConstellationImageUrl(
  variant: ImageVariant,
  abbreviation: string,
): Promise<string | null> {
  const key = cacheKey(variant, abbreviation);
  const cached = availabilityCache.get(key);
  if (cached) return cached;

  const load = (async () => {
    for (const url of candidateUrls(variant, abbreviation)) {
      if (await probeImageUrl(url)) return url;
    }
    return null;
  })();

  availabilityCache.set(key, load);
  return load;
}

/**
 * Resolve every available photograph URL for a constellation variant, in order
 * (base image first, then numbered variants). Returns an empty array when none
 * are available.
 */
export async function getConstellationImageUrls(
  variant: ImageVariant,
  abbreviation: string,
): Promise<string[]> {
  const found: string[] = [];
  for (const url of candidateUrls(variant, abbreviation)) {
    if (await probeImageUrl(url)) found.push(url);
  }
  return found;
}

/**
 * Synchronous helper returning the conventional WebP path for a variant.
 * Use this only when availability is already known (caller checked first);
 * otherwise prefer `resolveConstellationImageUrl` so the real on-disk file is
 * used instead of assuming an extension.
 */
export function resolveConstellationImage(
  variant: ImageVariant,
  abbreviation: string,
): string {
  return `${IMAGE_ROOT}/${variant}/${abbreviation.toLowerCase()}.webp`;
}

/**
 * Check whether a constellation photograph is available for the given variant.
 * Returns a promise that resolves to true when at least one supported
 * extension (base or numbered variant) exists at the expected path.
 */
export async function isConstellationImageAvailable(
  variant: ImageVariant,
  abbreviation: string,
): Promise<boolean> {
  return (await resolveConstellationImageUrl(variant, abbreviation)) !== null;
}

/**
 * Check both variants at once. Returns an object with availability for each.
 */
export async function checkConstellationImages(
  abbreviation: string,
): Promise<{ unannotated: boolean; annotated: boolean }> {
  const [unannotated, annotated] = await Promise.all([
    isConstellationImageAvailable("unannotated", abbreviation),
    isConstellationImageAvailable("annotated", abbreviation),
  ]);
  return { unannotated, annotated };
}

/**
 * Get the list of constellation IDs that have an available unannotated
 * photograph. Results are cached after the first probe pass.
 */
let eligibleCache: Promise<string[]> | null = null;

export function getEligibleConstellationIds(): Promise<string[]> {
  if (eligibleCache) return eligibleCache;

  eligibleCache = (async () => {
    const results = await Promise.all(
      constellations.map(async (c) => {
        const available = await isConstellationImageAvailable("unannotated", c.abbreviation);
        return available ? c.id : null;
      }),
    );
    return results.filter((id): id is string => id !== null);
  })();

  return eligibleCache;
}
