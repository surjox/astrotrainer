import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

const IMAGE_ROOT = "/messier";
const MAX_PROBE = 12;

// Shared last-viewed image index per Messier object so the detail view can
// open on the same image that was last browsed in a catalogue card.
const lastIndexByObject = new Map<string, number>();

interface LocalImageGalleryProps {
  objectId: string;
  alt: string;
  className?: string;
}

export function LocalImageGallery({ objectId, alt, className }: LocalImageGalleryProps) {
  const [available, setAvailable] = useState<number[]>([]);
  const [broken, setBroken] = useState<Set<number>>(new Set());
  const [currentIndex, setCurrentIndex] = useState(0);
  const [displayedIndex, setDisplayedIndex] = useState(0);
  const [opacity, setOpacity] = useState(1);
  const containerRef = useRef<HTMLDivElement>(null);

  const effective = available.filter((n) => !broken.has(n));
  const count = effective.length;
  const position = count > 0 ? ((currentIndex % count) + count) % count : 0;
  const currentNumber = count > 0 ? effective[position] : null;
  const currentSrc =
    currentNumber != null
      ? `${IMAGE_ROOT}/${objectId}/${String(currentNumber).padStart(2, "0")}.webp`
      : null;

  // Discover images by probing the sequential 01..MAX_PROBE paths.
  useEffect(() => {
    let settled = 0;
    const found: number[] = [];
    const failed = new Set<number>();

    const done = () => {
      settled += 1;
      if (settled === MAX_PROBE) {
        setAvailable(found.sort((a, b) => a - b));
        setBroken(failed);
      }
    };

    for (let n = 1; n <= MAX_PROBE; n += 1) {
      const img = new Image();
      img.src = `${IMAGE_ROOT}/${objectId}/${String(n).padStart(2, "0")}.webp`;
      img.onload = () => {
        found.push(n);
        done();
      };
      img.onerror = () => {
        failed.add(n);
        done();
      };
    }
  }, [objectId]);

  // Initialise from the shared store so the detail view can resume where the
  // catalogue card left off.
  useEffect(() => {
    if (count === 0) {
      setCurrentIndex(0);
      setDisplayedIndex(0);
      return;
    }
    const stored = lastIndexByObject.get(objectId);
    const start = stored != null ? Math.min(stored, count - 1) : 0;
    setCurrentIndex(start);
    setDisplayedIndex(start);
  }, [objectId, count]);

  // Persist the current index to the shared store.
  useEffect(() => {
    if (count > 0) lastIndexByObject.set(objectId, currentIndex);
  }, [objectId, currentIndex, count]);

  // Clamp indexes when the available set shrinks (e.g. a load failure).
  useEffect(() => {
    if (count === 0) {
      setCurrentIndex(0);
      setDisplayedIndex(0);
      return;
    }
    if (currentIndex >= count) setCurrentIndex(count - 1);
    if (displayedIndex >= count) setDisplayedIndex(count - 1);
  }, [count, currentIndex, displayedIndex]);

  // Cross-fade when the index changes.
  useEffect(() => {
    if (currentIndex === displayedIndex) return;
    setOpacity(0);
    const timer = setTimeout(() => {
      setDisplayedIndex(currentIndex);
      setOpacity(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [currentIndex, displayedIndex, count]);

  const goTo = useCallback(
    (index: number) => {
      if (count <= 1) return;
      setCurrentIndex(((index % count) + count) % count);
    },
    [count],
  );

  const goPrev = useCallback(() => goTo(currentIndex - 1), [currentIndex, goTo]);
  const goNext = useCallback(() => goTo(currentIndex + 1), [currentIndex, goTo]);

  const handleImageError = useCallback(() => {
    if (currentNumber == null) return;
    setBroken((prev) => {
      const next = new Set(prev);
      next.add(currentNumber);
      return next;
    });
  }, [currentNumber]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goPrev();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        goNext();
      }
    },
    [goPrev, goNext],
  );

  if (count === 0) {
    return (
      <div
        ref={containerRef}
        className={cn(
          "relative w-full min-h-56 sm:min-h-72 rounded-md overflow-hidden bg-secondary/10 flex items-center justify-center",
          className,
        )}
      >
        <div className="text-center">
          <p className="font-display text-base">Picture not found</p>
          <p className="mt-1 text-xs text-muted-foreground">Image will be added later.</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      tabIndex={0}
      role="region"
      aria-label={alt}
      onKeyDown={handleKeyDown}
      className={cn(
        "relative w-full min-h-56 sm:min-h-72 rounded-md overflow-hidden bg-secondary/10",
        className,
      )}
    >
      <div className="w-full h-full flex items-center justify-center">
        {currentSrc && (
          <img
            src={currentSrc}
            alt={alt}
            style={{ opacity }}
            className={cn(
              "w-full h-full max-w-full max-h-full object-contain rounded-md transition-opacity duration-300 ease-in-out",
            )}
            onLoad={() => setOpacity(1)}
            onError={handleImageError}
            loading="eager"
            decoding="async"
          />
        )}
      </div>

      {count > 1 && (
        <>
          <button
            type="button"
            style={{ translate: "0 0", transition: "none", WebkitTransition: "none" }}
            onClick={(event) => {
              event.stopPropagation();
              goPrev();
            }}
            aria-label="Previous image"
            className={cn(
              "absolute z-20 left-2 top-1/2 -translate-y-1/2",
              "flex items-center justify-center",
              "w-8 h-8 rounded-full",
              "bg-background/60 backdrop-blur-sm border border-border/60",
              "text-foreground/90 hover:bg-background/80 hover:text-foreground",
              "hover:[translate:0_0]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
              "disabled:pointer-events-none disabled:opacity-50",
            )}
          >
            <ArrowLeft className="size-4" />
            <span className="sr-only">Previous image</span>
          </button>
          <button
            type="button"
            style={{ translate: "0 0", transition: "none", WebkitTransition: "none" }}
            onClick={(event) => {
              event.stopPropagation();
              goNext();
            }}
            aria-label="Next image"
            className={cn(
              "absolute z-20 right-2 top-1/2 -translate-y-1/2",
              "flex items-center justify-center",
              "w-8 h-8 rounded-full",
              "bg-background/60 backdrop-blur-sm border border-border/60",
              "text-foreground/90 hover:bg-background/80 hover:text-foreground",
              "hover:[translate:0_0]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
              "disabled:pointer-events-none disabled:opacity-50",
            )}
          >
            <ArrowRight className="size-4" />
            <span className="sr-only">Next image</span>
          </button>
          <span className="absolute z-20 bottom-2 left-1/2 -translate-x-1/2 rounded-full bg-background/80 backdrop-blur border border-border/60 px-2.5 py-0.5 text-xs text-foreground">
            {position + 1} / {count}
          </span>
        </>
      )}
    </div>
  );
}
