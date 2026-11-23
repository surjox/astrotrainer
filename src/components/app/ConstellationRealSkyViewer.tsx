/**
 * Real-Sky Image viewer modal component.
 *
 * Displays an unannotated NOIRLab photograph of a constellation, with an
 * optional toggle to show the annotated version (constellation lines).
 * Gracefully handles missing images with a polished placeholder.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  resolveConstellationImageUrl,
} from "@/lib/astro/constellationImages";
import { cn } from "@/lib/utils";

interface ConstellationRealSkyViewerProps {
  abbreviation: string;
  name: string;
  onClose: () => void;
}

export function ConstellationRealSkyViewer({
  abbreviation,
  name,
  onClose,
}: ConstellationRealSkyViewerProps) {
  const [showAnnotated, setShowAnnotated] = useState(false);
  const [imageUrls, setImageUrls] = useState<{
    unannotated: string | null;
    annotated: string | null;
  }>({ unannotated: null, annotated: null });
  const [mounted, setMounted] = useState(false);
  const [imgLoading, setImgLoading] = useState(false);
  const [imgError, setImgError] = useState(false);
  // Tracks the URL we are currently waiting to load, used to discard stale events.
  const expectedUrlRef = useRef<string | null>(null);
  // Ref to the actual <img> DOM element so we can inspect .complete after mount.
  const imgRef = useRef<HTMLImageElement | null>(null);

  // Resolve the real on-disk photograph URL(s) after mount.
  useEffect(() => {
    setMounted(true);
    let active = true;

    const loadUrls = async () => {
      const [unannotated, annotated] = await Promise.all([
        resolveConstellationImageUrl("unannotated", abbreviation),
        resolveConstellationImageUrl("annotated", abbreviation),
      ]);
      if (active) {
        setImageUrls({ unannotated, annotated });
      }
    };

    void loadUrls();

    return () => {
      active = false;
    };
  }, [abbreviation]);

  const toggleAnnotated = useCallback(() => {
    setShowAnnotated((prev) => !prev);
  }, []);

  const imageVariant = showAnnotated ? "annotated" : "unannotated";
  const imageUrl = imageUrls[imageVariant];
  const imageAvailable = imageUrl !== null;
  const canToggle = imageUrls.annotated !== null;

  // When the target URL changes: mark as loading and update the expected-URL
  // ref so stale events from older images are ignored.
  //
  // IMPORTANT: resolveConstellationImageUrl returns a relative path such as
  // "/images/constellations/real-sky/unannotated/ori.webp", but the browser
  // always exposes img.src as a fully-qualified absolute URL
  // ("http://localhost:3000/images/..."). We normalise to an absolute URL here
  // so that every comparison against img.src succeeds.
  //
  // After updating the ref we also check whether the browser has already
  // loaded this image from cache (img.complete && img.naturalWidth > 0).
  // resolveConstellationImageUrl pre-probes URLs via hidden Image objects, so
  // by the time our <img> mounts the browser cache is usually warm and onLoad
  // fires synchronously during mount — before this useEffect can run.
  useEffect(() => {
    if (!imageUrl) return;

    // Normalise relative → absolute so it matches img.src.
    const absUrl = new URL(imageUrl, window.location.href).href;
    expectedUrlRef.current = absUrl;
    setImgLoading(true);
    setImgError(false);

    // Check whether the element already finished loading from cache.
    // useEffect runs after the DOM is painted, so .complete may already be true.
    const el = imgRef.current;
    if (el && el.complete) {
      if (el.naturalWidth > 0) {
        setImgLoading(false);
        setImgError(false);
      } else {
        // complete with naturalWidth === 0 means the load failed
        setImgLoading(false);
        setImgError(true);
      }
    }
  }, [imageUrl]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    },
    [onClose],
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-label={`${name} real-sky photograph`}
      onKeyDown={handleKeyDown}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className={cn(
          "flex h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl border border-border bg-background shadow-2xl",
          "relative",
        )}
      >
        {/* Modal header */}
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div className="min-w-0">
            <h2 className="font-display text-lg font-semibold">{name}</h2>
            <p className="text-xs text-muted-foreground font-mono">{abbreviation}</p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Close real-sky image viewer"
          >
            <X className="size-5" />
          </Button>
        </div>

        {/* Image area */}
        <div className="min-h-0 flex-1 flex items-center justify-center bg-secondary/10 p-4 sm:p-6 overflow-hidden relative">
          {!mounted ? (
            <div className="text-muted-foreground text-sm p-8 bg-slate-800 rounded">
              Loading photograph…
            </div>
          ) : !imageAvailable ? (
            <div className="text-center max-w-md">
              <div className="rounded bg-secondary/20 border border-border/60 p-8 text-center">
                <p className="font-display text-base">Photograph not yet added</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  The real-sky photograph for <span className="text-foreground">{name}</span> ({abbreviation}) has not been uploaded yet.
                </p>
              </div>
              {imageVariant === "unannotated" && imageUrls.annotated === null && (
                <div className="mt-4">
                  <p className="text-xs text-muted-foreground">
                    Annotated version also not yet available.
                  </p>
                </div>
              )}
            </div>
          ) : (
            <>
              {imgLoading && (
                <div
                  role="status"
                  className="text-muted-foreground text-sm p-8 bg-slate-800 rounded"
                >
                  Loading constellation image...
                </div>
              )}
              {imgError && !imgLoading && (
                <div className="text-muted-foreground text-sm p-8 bg-slate-800 rounded">
                  <p>Image could not be loaded.</p>
                </div>
              )}
              <img
                ref={imgRef}
                src={imageUrl}
                alt={`${name} ${imageVariant} real-sky photograph`}
                className={cn(
                  "max-w-full max-h-[65vh] mx-auto object-contain rounded",
                  (imgLoading || imgError) && "hidden",
                )}
                loading="eager"
                onLoad={(e) => {
                  const el = e.target as HTMLImageElement;
                  if (el.src === expectedUrlRef.current) {
                    setImgLoading(false);
                    // naturalWidth > 0 confirms a real successful load, not an
                    // error that browser reports as onLoad in some edge cases.
                    setImgError(el.naturalWidth === 0);
                  }
                }}
                onError={(e) => {
                  if ((e.target as HTMLImageElement).src === expectedUrlRef.current) {
                    setImgLoading(false);
                    setImgError(true);
                  }
                }}
              />
              {showAnnotated && imageUrls.annotated === null && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full bg-background/80 backdrop-blur border border-border/60 px-3 py-1 text-xs text-muted-foreground">
                  Annotated image not available
                </div>
              )}
            </>
          )}

          {/* Annotation toggle (only when unannotated image is available and annotated exists) */}
          {imageAvailable && imageVariant === "unannotated" && imageUrls.annotated !== null && (
            <Button
              variant="secondary"
              size="sm"
              onClick={toggleAnnotated}
              disabled={!canToggle}
              className="absolute bottom-4 right-4"
            >
              {canToggle ? "Show constellation lines" : "Annotated image not available"}
            </Button>
          )}

          {showAnnotated && imageVariant === "annotated" && imageUrls.annotated !== null && (
            <Button
              variant="secondary"
              size="sm"
              onClick={toggleAnnotated}
              className="absolute bottom-4 right-4"
            >
              Hide constellation lines
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
