/**
 * Lightweight, non-interactive sky-map preview for star patterns.
 *
 * Renders stars and connecting lines as SVG using the existing Projection
 * class. No canvas, no ResizeObserver, no interaction — safe to render on
 * every card in a grid.
 */

import { useMemo } from "react";
import { starById } from "@/lib/astro/catalog";
import { resolveStarRef } from "@/lib/astro/asterisms";
import { fitConstellation } from "@/lib/astro/fov";
import { Projection } from "@/lib/astro/projection";
import type { Constellation, Star } from "@/lib/astro/types";
import { cn } from "@/lib/utils";

interface StarPatternPreviewProps {
  /** Stars to render (indices into this array are used by `lines`) */
  stars: Star[];
  /** Connecting segments as index pairs into `stars` */
  lines: [number, number][];
  /** Optional center for framing (falls back to centroid of stars) */
  center?: { ra: number; dec: number } | undefined;
  width?: number | string;
  height?: number | string;
  className?: string | undefined;
}

interface ConstellationPreviewProps {
  constellation: Constellation;
  width?: number | string;
  height?: number | string;
  className?: string;
}

function starRadius(mag: number): number {
  const base = 0.55 * Math.pow(1.52, Math.max(-1.5, 6.4 - mag));
  return Math.min(3, Math.max(0.8, base));
}

function starColor(spect: string | null): string {
  const t = (spect ?? "").charAt(0).toUpperCase();
  switch (t) {
    case "O": return "#b9d0ff";
    case "B": return "#c9dbff";
    case "A": return "#e9efff";
    case "F": return "#fffdf4";
    case "G": return "#fff1c4";
    case "K": return "#ffd6a3";
    case "M": return "#ffb98d";
    default: return "#f2f5ff";
  }
}

function StarPatternPreview({
  stars,
  lines,
  center,
  width,
  height,
  className,
}: StarPatternPreviewProps) {
  const svg = useMemo(() => {
    if (stars.length === 0) return null;

    // Frame on the provided center or compute centroid
    let viewCenter = center;
    if (!viewCenter && stars.length > 0) {
      let x = 0, y = 0, z = 0;
      const DEG = Math.PI / 180;
      for (const s of stars) {
        const ra = s.ra * DEG;
        const dec = s.dec * DEG;
        x += Math.cos(dec) * Math.cos(ra);
        y += Math.cos(dec) * Math.sin(ra);
        z += Math.sin(dec);
      }
      const r = Math.hypot(x, y, z) || 1;
      viewCenter = {
        ra: (((Math.atan2(y, x) / DEG) % 360) + 360) % 360,
        dec: Math.asin(z / r) / DEG,
      };
    }

    if (!viewCenter) return null;

    const view = { ra: viewCenter.ra, dec: viewCenter.dec, fov: 40, rotation: 0 };
    const proj = new Projection(view, 400, 300);

    const positions = new Map<number, { x: number; y: number }>();
    for (const s of stars) {
      const p = proj.project(s.ra, s.dec);
      if (p) positions.set(s.id, p);
    }

    if (positions.size === 0) return null;

    const allX = [...positions.values()].map((p) => p.x);
    const allY = [...positions.values()].map((p) => p.y);
    const minX = Math.min(...allX) - 20;
    const maxX = Math.max(...allX) + 20;
    const minY = Math.min(...allY) - 20;
    const maxY = Math.max(...allY) + 20;
    const viewBox = `${minX.toFixed(0)} ${minY.toFixed(0)} ${(maxX - minX).toFixed(0)} ${(maxY - minY).toFixed(0)}`;

    const lineSegments = lines.map(([a, b]) => {
      const pa = positions.get(stars[a]?.id ?? -1);
      const pb = positions.get(stars[b]?.id ?? -1);
      if (!pa || !pb) return null;
      return (
        <path
          key={`line-${a}-${b}`}
          d={`M ${pa.x.toFixed(1)},${pa.y.toFixed(1)} L ${pb.x.toFixed(1)},${pb.y.toFixed(1)}`}
          stroke="rgba(85,183,255,0.55)"
          strokeWidth={1.2}
          strokeLinecap="round"
          fill="none"
        />
      );
    });

    const starCircles = stars.map((s) => {
      const p = positions.get(s.id);
      if (!p) return null;
      const r = starRadius(s.magnitude);
      return (
        <circle
          key={s.id}
          cx={p.x.toFixed(1)}
          cy={p.y.toFixed(1)}
          r={r.toFixed(2)}
          fill={starColor(s.spectralType)}
          opacity={0.95}
        />
      );
    });

    return (
      <svg
        viewBox={viewBox}
        preserveAspectRatio="xMidYMid meet"
        className={cn(
          "w-full h-full rounded-md border border-border/60 bg-secondary/20",
          className,
        )}
        style={{ width, height, display: "block" }}
      >
        {lineSegments}
        {starCircles}
      </svg>
    );
  }, [stars, lines, center, width, height, className]);

  if (!svg) {
    return (
      <div
        className={cn(
          "w-full flex items-center justify-center rounded-md border border-border/60 bg-secondary/20",
          className,
        )}
        style={{ width, height }}
      >
        <span className="text-[10px] text-muted-foreground">Preview unavailable</span>
      </div>
    );
  }

  return <div className="w-full min-h-[150px]">{svg}</div>;
}

export function ConstellationPreview({
  constellation,
  width = "100%",
  height = 150,
  className,
}: ConstellationPreviewProps) {
  // Resolve figure stars from HIP ids
  const resolvedStars = constellation.figureStars
    .map((hip) => starById.get(hip))
    .filter((s): s is Star => !!s);

  // constellation.lineData contains HIP id pairs (authoritative IAU line data).
  // Convert them to index pairs into `resolvedStars` so StarPatternPreview can
  // look up positions from its star-indexed `positions` map.
  const lineIndices = constellation.lineData
    .map(([hipA, hipB]) => {
      const ia = resolvedStars.findIndex((s) => s.id === hipA);
      const ib = resolvedStars.findIndex((s) => s.id === hipB);
      return ia >= 0 && ib >= 0 ? ([ia, ib] as [number, number]) : null;
    })
    .filter((pair): pair is [number, number] => pair !== null);

  return (
    <StarPatternPreview
      stars={resolvedStars}
      lines={lineIndices}
      center={{ ra: constellation.centerRa, dec: constellation.centerDec }}
      width={width}
      height={height}
      className={className}
    />
  );
}

export interface AsterismPreviewProps {
  asterism: {
    name: string;
    principalStars: string[];
    lines: [number, number][];
    centerRa?: number;
    centerDec?: number;
  };
  width?: number | string;
  height?: number | string;
  className?: string;
}

export function AsterismPreview({
  asterism,
  width = "100%",
  height = 150,
  className,
}: AsterismPreviewProps) {
  // Resolve principal star designations to Star objects
  const resolvedStars: Star[] = [];
  for (const ref of asterism.principalStars) {
    const star = resolveStarRef(ref);
    if (star) resolvedStars.push(star);
  }

  const center = asterism.centerRa != null && asterism.centerDec != null
    ? { ra: asterism.centerRa, dec: asterism.centerDec }
    : undefined;

  return (
    <StarPatternPreview
      stars={resolvedStars}
      lines={asterism.lines}
      center={center}
      width={width}
      height={height}
      className={className}
    />
  );
}
