import { Link } from "@tanstack/react-router";
import { Menu, X } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

const links = [
  { to: "/", label: "Home" },
  { to: "/practice", label: "Practice" },
  { to: "/constellations", label: "Constellations" },
  { to: "/asterisms", label: "Asterisms" },
  { to: "/messier", label: "Messier" },
  { to: "/sky-map", label: "Sky Map" },
  { to: "/progress", label: "Progress" },
] as const;

export function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 sm:px-6">
        <Link
          to="/"
          className="inline-flex shrink-0 items-center gap-3 rounded-full border border-border/80 bg-card/60 px-2.5 py-2 text-foreground shadow-sm"
          onClick={() => setOpen(false)}
        >
          <span className="inline-flex size-2.5 rounded-full bg-primary shadow-[0_0_16px_rgba(133,180,255,0.9)]" />
          <span className="font-display text-[0.68rem] font-semibold tracking-[0.22em] sm:text-[0.74rem]">
            ASTRO<span className="text-primary">TRAINER</span>
          </span>
        </Link>

        <nav className="ml-auto hidden items-center gap-1 px-1 py-1 lg:flex">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              activeOptions={{ exact: l.to === "/" }}
              className="whitespace-nowrap rounded-full px-3 py-2 text-sm font-medium text-muted-foreground transition-all duration-150 hover:bg-secondary/70 hover:text-foreground"
              activeProps={{
                className:
                  "bg-secondary text-foreground shadow-sm ring-1 ring-border/70 shadow-[0_8px_18px_rgba(15,23,42,0.18)]",
              }}
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <button
          type="button"
          className="ml-auto inline-flex size-10 items-center justify-center rounded-md border border-border/80 bg-card/60 text-foreground lg:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="mobile-nav"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>

      <div
        id="mobile-nav"
        className={cn(
          "border-t border-border/70 bg-background/95 px-4 py-3 backdrop-blur-xl lg:hidden",
          open ? "block" : "hidden",
        )}
      >
        <nav className="mx-auto grid max-w-7xl gap-1 sm:grid-cols-2">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              activeOptions={{ exact: l.to === "/" }}
              onClick={() => setOpen(false)}
              className="rounded-md px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary/70 hover:text-foreground"
              activeProps={{
                className: "bg-secondary text-foreground ring-1 ring-border/70",
              }}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
