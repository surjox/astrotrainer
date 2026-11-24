from pathlib import Path
from PIL import Image
import shutil


# ============================================================
# PATHS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

BASE_DIR = PROJECT_DIR / "public" / "iau-constellations"

INPUT_DIR = BASE_DIR / "processed-new"
OUTPUT_DIR = BASE_DIR / "processed"

TEMP_DIR = BASE_DIR / "webp-temp"


# ============================================================
# SETTINGS
# ============================================================

WEBP_QUALITY = 90
WEBP_METHOD = 6


# ============================================================
# MAIN
# ============================================================

def main():

    if not INPUT_DIR.exists():
        print(f"Input folder not found: {INPUT_DIR}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Find all JPEG files
    jpeg_files = sorted(
        [
            file for file in INPUT_DIR.iterdir()
            if file.is_file()
            and file.suffix.lower() in (".jpg", ".jpeg")
        ]
    )

    if not jpeg_files:
        print("No JPEG files found.")
        return

    print("=" * 60)
    print("JPEG TO WEBP CONVERSION")
    print("=" * 60)

    print(f"JPEG files found: {len(jpeg_files)}")

    # Clean temporary directory
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)

    TEMP_DIR.mkdir(parents=True)

    converted_files = []

    # ========================================================
    # CONVERT JPEGs TO WEBP
    # ========================================================

    for index, jpeg_path in enumerate(jpeg_files, start=1):

        webp_path = TEMP_DIR / (
            jpeg_path.stem + ".webp"
        )

        print(
            f"\n[{index}/{len(jpeg_files)}] "
            f"Converting: {jpeg_path.name}"
        )

        try:

            with Image.open(jpeg_path) as img:

                img.save(
                    webp_path,
                    "WEBP",
                    quality=WEBP_QUALITY,
                    method=WEBP_METHOD
                )

            converted_files.append(webp_path)

            original_size = jpeg_path.stat().st_size
            compressed_size = webp_path.stat().st_size

            reduction = (
                (1 - compressed_size / original_size) * 100
            )

            print(
                f"  {original_size / 1024:.1f} KB -> "
                f"{compressed_size / 1024:.1f} KB"
            )

            print(f"  Size reduction: {reduction:.1f}%")

        except Exception as e:

            print(f"  Conversion failed: {e}")

    # ========================================================
    # VERIFY CONVERSIONS
    # ========================================================

    print("\n" + "=" * 60)
    print("CONVERSION SUMMARY")
    print("=" * 60)

    print(f"Total JPEGs: {len(jpeg_files)}")
    print(f"Successfully converted: {len(converted_files)}")
    print(f"Failed: {len(jpeg_files) - len(converted_files)}")

    if not converted_files:
        print("\nNo files converted. Existing processed folder untouched.")
        shutil.rmtree(TEMP_DIR)
        return

    # ========================================================
    # REPLACE EXISTING PROCESSED FILES
    # ========================================================

    print("\nReplacing files inside processed/ ...")

    # Delete all existing files recursively
    for file in OUTPUT_DIR.rglob("*"):

        if file.is_file() or file.is_symlink():
            file.unlink()

    # Move converted WebPs into processed/
    for webp_path in converted_files:

        destination = OUTPUT_DIR / webp_path.name

        shutil.move(
            str(webp_path),
            str(destination)
        )

    # Remove temporary directory
    shutil.rmtree(TEMP_DIR)

    # ========================================================
    # FINAL REPORT
    # ========================================================

    final_files = list(OUTPUT_DIR.glob("*.webp"))

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)

    print(f"WebP files in processed/: {len(final_files)}")
    print(f"Output location: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()