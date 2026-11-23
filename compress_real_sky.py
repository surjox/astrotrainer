
import argparse
import csv
import shutil
import sys
import warnings
from pathlib import Path

from PIL import Image, ImageSequence

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent

SOURCE_DIR = (
    PROJECT_DIR
    / "public"
    / "images"
    / "constellations"
    / "real-sky"
)

OUTPUT_DIR = PROJECT_DIR / "compressed"

REPORT_PATH = OUTPUT_DIR / "real_sky_compression_report.csv"

DEFAULT_QUALITY = 60
METHOD = 6

# Large astronomical images can trigger Pillow warnings.
warnings.simplefilter("ignore", Image.DecompressionBombWarning)


# --------------------------------------------------
# UTILITIES
# --------------------------------------------------

def format_size(size):
    units = ["B", "KB", "MB", "GB", "TB"]

    size = float(size)

    for unit in units:
        if size < 1024 or unit == "TB":
            return f"{size:.2f} {unit}"
        size /= 1024

    return f"{size:.2f} TB"


def get_images():
    return sorted(
        p for p in SOURCE_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() == ".webp"
    )


def preserve_original(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


# --------------------------------------------------
# COMPRESSION
# --------------------------------------------------

def compress_image(source, destination, quality):
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        with Image.open(source) as image:

            original_dimensions = image.size
            animated = getattr(image, "is_animated", False)
            frame_count = getattr(image, "n_frames", 1)

            save_options = {
                "format": "WEBP",
                "quality": quality,
                "method": METHOD,
            }

            # Preserve ICC and EXIF metadata when available.
            if image.info.get("icc_profile"):
                save_options["icc_profile"] = image.info["icc_profile"]

            if image.info.get("exif"):
                save_options["exif"] = image.info["exif"]

            if animated and frame_count > 1:
                frames = []
                durations = []

                for frame in ImageSequence.Iterator(image):
                    frames.append(frame.copy())
                    durations.append(frame.info.get("duration", 100))

                save_options.update({
                    "save_all": True,
                    "append_images": frames[1:],
                    "duration": durations,
                    "loop": image.info.get("loop", 0),
                    "lossless": False,
                })

                frames[0].save(destination, **save_options)

                for frame in frames:
                    frame.close()

            else:
                image.save(destination, **save_options)

        # Verify output.
        with Image.open(destination) as result:
            compressed_dimensions = result.size

            if compressed_dimensions != original_dimensions:
                raise ValueError(
                    f"Dimensions changed: "
                    f"{original_dimensions} -> {compressed_dimensions}"
                )

            if getattr(result, "n_frames", 1) != frame_count:
                raise ValueError("Frame count changed during compression")

        original_size = source.stat().st_size
        compressed_size = destination.stat().st_size

        # Keep original if compression increased file size.
        if compressed_size >= original_size:
            preserve_original(source, destination)
            compressed_size = original_size
            status = "Original retained (no size reduction)"
        else:
            status = "Compressed successfully"

        saved_percent = (
            (original_size - compressed_size)
            / original_size * 100
            if original_size else 0
        )

        return {
            "filename": str(source.relative_to(SOURCE_DIR)),
            "dimensions": f"{original_dimensions[0]}x{original_dimensions[1]}",
            "original_size": original_size,
            "compressed_size": compressed_size,
            "saved_percent": round(saved_percent, 2),
            "animation": "Yes" if animated else "No",
            "status": status,
        }

    except Exception as error:
        # Never leave a missing output if processing fails.
        preserve_original(source, destination)

        return {
            "filename": str(source.relative_to(SOURCE_DIR)),
            "dimensions": "Unknown",
            "original_size": source.stat().st_size,
            "compressed_size": destination.stat().st_size,
            "saved_percent": 0,
            "animation": "Unknown",
            "status": f"Failed; original copied: {error}",
        }


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Aggressively compress Real Sky WebP images."
    )

    parser.add_argument(
        "--quality",
        type=int,
        default=DEFAULT_QUALITY,
        choices=range(1, 101),
        metavar="1-100",
        help="WebP quality (default: 60)"
    )

    args = parser.parse_args()

    if not SOURCE_DIR.exists():
        print(f"Source directory not found:\n{SOURCE_DIR}")
        sys.exit(1)

    images = get_images()

    if not images:
        print("No WebP images found.")
        sys.exit(0)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("REAL SKY IMAGE COMPRESSION")
    print("=" * 60)
    print(f"Source:  {SOURCE_DIR}")
    print(f"Output:  {OUTPUT_DIR}")
    print(f"Images:  {len(images)}")
    print(f"Quality: {args.quality}")
    print(f"Method:  {METHOD}")
    print("=" * 60)

    results = []

    total_original = 0
    total_compressed = 0

    for index, source in enumerate(images, start=1):

        relative_path = source.relative_to(SOURCE_DIR)
        destination = OUTPUT_DIR / relative_path

        print(
            f"[{index}/{len(images)}] "
            f"{relative_path}",
            end=" ... ",
            flush=True
        )

        result = compress_image(
            source,
            destination,
            args.quality
        )

        results.append(result)

        total_original += result["original_size"]
        total_compressed += result["compressed_size"]

        print(
            f"{format_size(result['original_size'])} -> "
            f"{format_size(result['compressed_size'])} "
            f"({result['saved_percent']}% saved)"
        )

    # Generate CSV report.
    with REPORT_PATH.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as csvfile:

        fieldnames = [
            "filename",
            "dimensions",
            "original_size",
            "compressed_size",
            "saved_percent",
            "animation",
            "status",
        ]

        writer = csv.DictWriter(
            csvfile,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)

    total_saved = total_original - total_compressed

    reduction = (
        total_saved / total_original * 100
        if total_original else 0
    )

    failures = sum(
        1 for result in results
        if result["status"].startswith("Failed")
    )

    print("\n" + "=" * 60)
    print("COMPRESSION COMPLETE")
    print("=" * 60)

    print(f"Images processed: {len(images)}")
    print(f"Original size:    {format_size(total_original)}")
    print(f"Compressed size:  {format_size(total_compressed)}")
    print(f"Space saved:      {format_size(total_saved)}")
    print(f"Reduction:        {reduction:.2f}%")
    print(f"Failed images:    {failures}")

    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"CSV report:       {REPORT_PATH}")

    print("=" * 60)


if __name__ == "__main__":
    main()
