import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Search, Shuffle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { AsterismPreview } from "@/components/app/ConstellationPreview";
import { Input } from "@/components/ui/input";
import {
  ASTERISM_CATEGORIES,
  asterisms,
  searchAsterisms,
  type AsterismCategory,
} from "@/lib/astro/asterisms";
import { starLabelWithBayer } from "@/lib/astro/catalog";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/asterisms/")({
  head: () => ({
    meta: [
      { title: "Asterisms — Recognisable Star Patterns | AstroTrainer" },
      {
        name: "description",
        content:
          "Browse the Big Dipper, Summer Triangle, Teapot and more: recognisable star patterns that are not official constellations, with real stars, interactive maps and observation notes.",
      },
      { property: "og:title", content: "Asterisms — Recognisable Star Patterns" },
      {
        property: "og:description",
        content:
          "An atlas of asterisms with principal stars, parent constellations, difficulty and interactive J2000 sky maps.",
      },
    ],
  }),
  component: AsterismAtlas,
});

const CATEGORIES = ["All", ...ASTERISM_CATEGORIES] as const;
type Filter = (typeof CATEGORIES)[number];

const DIFFICULTY_LABEL: Record<string, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

function AsterismAtlas() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Filter>("All");

  const list = useMemo(() => {
    const found = searchAsterisms(query);
    return category === "All"
      ? found
      : found.filter((a) => a.categories.includes(category as AsterismCategory));
  }, [query, category]);

  const random = () => {
    const a = asterisms[Math.floor(Math.random() * asterisms.length)]!;
    navigate({ to: "/asterisms/$id", params: { id: a.id } });
  };

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold">Asterisms</h1>
          <p className="mt-1 max-w-prose text-sm text-muted-foreground">
            Asterisms are recognisable star patterns that are <em>not</em> officially designated
            constellations. They may sit inside one constellation or span several, and unlike the 88
            IAU constellations there is no single authoritative list — where sources disagree, each
            entry records the alternative definitions.
          </p>
        </div>
        <Button variant="secondary" onClick={random} className="gap-2">
          <Shuffle className="size-4" />
          Random Asterism
        </Button>
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative sm:max-w-xs sm:flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search name, star or constellation..."
            aria-label="Search asterisms"
            className="pl-9"
          />
        </div>
        <span className="font-mono text-xs text-muted-foreground sm:ml-auto">
          {list.length} of {asterisms.length}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-1">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            onClick={() => setCategory(c)}
            className={cn(
              "rounded-md border border-border px-3 py-1.5 text-xs transition-colors",
              category === c
                ? "border-primary/60 bg-primary/15 text-foreground"
                : "text-muted-foreground hover:bg-secondary/60",
            )}
          >
            {c}
          </button>
        ))}
      </div>

      <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {list.map((a) => (
          <li
            key={a.id}
            className={cn(
              "panel flex flex-col p-4",
              "motion-safe:hover:-translate-y-1 motion-safe:hover:scale-[1.01] motion-safe:hover:border-primary/50 motion-safe:hover:shadow-[0_18px_36px_rgba(2,8,18,0.32)]",
              "transition-transform transition-box-shadow transition-border duration-200 ease-out",
            )}
          >
            {/* Sky-map preview */}
            <AsterismPreview
              asterism={{
                name: a.name,
                principalStars: a.principalStars,
                lines: a.lines,
              }}
              className="mb-3"
            />

            <div className="flex items-baseline justify-between gap-2">
              <h2 className="font-display text-lg font-semibold">{a.name}</h2>
              <span className="font-mono text-xs text-muted-foreground">
                {DIFFICULTY_LABEL[a.difficulty]}
              </span>
            </div>
            <p className="text-sm text-primary">{a.type}</p>
            {a.aliases.length > 0 && (
              <p className="mt-0.5 text-xs text-muted-foreground">Also: {a.aliases.join(", ")}</p>
            )}
            <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-muted-foreground">
              {a.description}
            </p>

            <p className="mt-3 text-xs">
              <span className="label-caps">In </span>
              <span className="text-muted-foreground">{a.constellationNames.join(", ")}</span>
            </p>

            {/* Principal stars */}
            <div className="mt-1 flex flex-wrap gap-1.5">
              <span className="label-caps block mb-1.5 text-xs w-full">Principal stars</span>
              {a.stars.slice(0, 4).map((s) => {
                const label = starLabelWithBayer(s);
                const [name, designation] = label.split(" — ");
                return (
                  <span
                    key={s.id}
                    className="rounded border border-border/80 bg-secondary/50 px-2 py-1 text-xs flex flex-wrap items-center gap-1"
                  >
                    <span className="text-foreground">{name}</span>
                    {designation && <span className="text-muted-foreground">{designation}</span>}
                  </span>
                );
              })}
              {a.stars.slice(0, 4).length === 0 && <span className="text-muted-foreground">—</span>}
              {a.stars.length > 4 && (
                <span className="rounded border border-border/80 bg-secondary/50 px-2 py-1 text-xs text-muted-foreground">
                  +{a.stars.length - 4}
                </span>
              )}
            </div>

            {/* Recognition */}
            <div className="mt-1">
              <span className="label-caps block text-xs mb-1">Recognition</span>
              <p className="text-sm leading-relaxed text-muted-foreground">{a.recognition}</p>
            </div>

            {a.bestSeason && (
              <div className="mt-1 flex items-center gap-2">
                <span className="label-caps text-xs">Best observed</span>
                <span className="rounded border border-primary/40 bg-primary/10 px-2 py-0.5 text-xs text-primary">
                  {a.bestSeason}
                </span>
              </div>
            )}

            <div className="mt-4 flex flex-wrap gap-2">
              <Button asChild variant="secondary" size="sm">
                <Link to="/asterisms/$id" params={{ id: a.id }}>
                  View in Sky
                </Link>
              </Button>
            </div>
          </li>
        ))}
      </ul>

      {list.length === 0 && (
        <p className="mt-10 text-center text-sm text-muted-foreground">
          No asterism matches “{query}”.
        </p>
      )}
    </main>
  );
}
