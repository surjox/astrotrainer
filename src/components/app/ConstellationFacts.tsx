import { importantStars, starLabelWithBayer } from "@/lib/astro/catalog";
import type { Constellation } from "@/lib/astro/types";

/** The educational payload shown identically at every difficulty after answering. */
export function ConstellationFacts({ constellation }: { constellation: Constellation }) {
  const keyStars = importantStars(constellation);
  return (
    <div className="space-y-4">
      {/* ====================================================== */}
      {/* HEADER                                                 */}
      {/* ====================================================== */}
      <div>
        <h3 className="font-display text-2xl font-semibold tracking-wide">
          {constellation.name.toUpperCase()}
        </h3>
        <div className="flex items-center gap-2 mt-1">
          <span className="font-mono text-xs text-muted-foreground">
            {constellation.abbreviation}
          </span>
          <p className="text-sm text-primary">{constellation.figure}</p>
        </div>
      </div>

      {/* ====================================================== */}
      {/* PRIMARY INFORMATION                                    */}
      {/* ====================================================== */}
      <div>
        <p className="label-caps block text-xs mb-1">Description</p>
        <p className="text-sm leading-relaxed text-muted-foreground">{constellation.description}</p>
      </div>

      {/* ====================================================== */}
      {/* ASTRONOMICAL DETAILS                                   */}
      {/* ====================================================== */}
      <dl className="grid grid-cols-2 gap-3">
        <div className="panel p-3">
          <dt className="label-caps">Abbreviation</dt>
          <dd className="mt-1 font-mono text-xs">{constellation.abbreviation}</dd>
        </div>
        <div className="panel p-3">
          <dt className="label-caps">Best observed</dt>
          <dd className="mt-1">
            <span className="rounded border border-primary/40 bg-primary/10 px-2 py-0.5 text-xs text-primary">
              {constellation.bestSeason}
            </span>
          </dd>
        </div>
        <div className="panel p-3">
          <dt className="label-caps">Region</dt>
          <dd className="mt-1 text-xs text-muted-foreground">
            {constellation.region}
            {constellation.isEcliptic ? " · Ecliptic" : ""}
          </dd>
        </div>
        <div className="panel p-3">
          <dt className="label-caps">Centre</dt>
          <dd className="mt-1 font-mono text-xs text-muted-foreground">
            {(constellation.centerRa / 15).toFixed(1)}h {constellation.centerDec.toFixed(0)}°
          </dd>
        </div>
      </dl>

      {/* ====================================================== */}
      {/* BRIGHT STARS                                           */}
      {/* ====================================================== */}
      {keyStars.length > 0 && (
        <div>
          <p className="label-caps block text-xs mb-1.5">Bright stars</p>
          <ul className="flex flex-wrap gap-1.5">
            {keyStars.map((s) => {
              const label = starLabelWithBayer(s);
              const [name, designation] = label.split(" — ");
              return (
                <li
                  key={s.id}
                  className="rounded border border-border/80 bg-secondary/50 px-2 py-1 text-xs flex flex-wrap items-center gap-1"
                >
                  <span className="text-foreground">{name}</span>
                  {designation && <span className="text-muted-foreground">{designation}</span>}
                  <span className="font-mono text-[10px] text-muted-foreground">
                    m{s.magnitude.toFixed(2)}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
