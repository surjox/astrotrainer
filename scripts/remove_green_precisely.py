
from pathlib import Path
import pymupdf
import fitz
from PIL import Image
import cv2
import numpy as np
import io
import json
import os

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SOURCE_DIR = PROJECT_ROOT / "public" / "iau-constellations"

TEXT_REMOVED_DIR = SOURCE_DIR / "text-removed"

INPUT_DIR = TEXT_REMOVED_DIR

OUTPUT_DIR = SOURCE_DIR / "processed-new"

TEXT_REMOVED_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

QA_LOG_PATH = OUTPUT_DIR / "green_removal_qa.json"


# ============================================================
# SETTINGS
# ============================================================

DPI = 300
JPEG_QUALITY = 95

# Green detection
HUE_LOW = 25
HUE_HIGH = 100

MIN_SATURATION = 20
MIN_VALUE = 20

# Region classification
WHITE_THRESHOLD = 238

INPAINT_RADIUS = 7


# ============================================================
# STEP 1: TEXT REMOVAL
# ============================================================

def remove_text(pdf_path):

    print(f"\nRemoving text: {pdf_path.name}")

    try:
        doc = fitz.open(pdf_path)

    except Exception as e:
        print(f"  Could not open PDF: {e}")
        return False

    total_spans = 0

    try:

        for page_number, page in enumerate(doc):

            # Extract all selectable text spans
            text_dict = page.get_text("dict")

            for block in text_dict["blocks"]:

                if "lines" not in block:
                    continue

                for line in block["lines"]:

                    for span in line["spans"]:

                        if not span["text"].strip():
                            continue

                        # Get text bounding box
                        rect = fitz.Rect(span["bbox"])

                        # Add redaction annotation
                        page.add_redact_annot(
                            rect,
                            fill=False,
                            cross_out=False
                        )

                        total_spans += 1

            # Apply redactions while preserving images
            # and vector graphics where possible.
            page.apply_redactions(
                images=0,
                graphics=0,
                text=0
            )

        # Save to separate output folder
        output_path = TEXT_REMOVED_DIR / pdf_path.name

        doc.save(
            str(output_path),
            garbage=4,
            deflate=True
        )

        print(f"  Text spans removed: {total_spans}")
        print(f"  Saved: {output_path.name}")

        return True

    except Exception as e:

        print(f"  Text removal failed: {e}")
        return False

    finally:

        doc.close()


# ============================================================
# GREEN DETECTION
# ============================================================

def detect_green_mask(rgb):

    hsv = cv2.cvtColor(
        rgb,
        cv2.COLOR_RGB2HSV
    )

    h, s, v = cv2.split(hsv)

    mask = (
        (h >= HUE_LOW) &
        (h <= HUE_HIGH) &
        (s >= MIN_SATURATION) &
        (v >= MIN_VALUE)
    )

    return mask


# ============================================================
# GREEN REMOVAL
# KEEP EXACTLY AS PROVIDED
# ============================================================

def remove_green(rgb):

    original = rgb.copy()

    mask = detect_green_mask(original)

    result = original.copy()

    # Replace detected green pixels with white
    result[mask] = [255, 255, 255]

    remaining_mask = detect_green_mask(result)

    removed_pixels = int(np.count_nonzero(mask))
    remaining_pixels = int(np.count_nonzero(remaining_mask))

    unchanged = np.array_equal(
        original[~mask],
        result[~mask]
    )

    return (
        result,
        removed_pixels,
        remaining_pixels,
        unchanged
    )


# ============================================================
# CONSTELLATION REGION CLASSIFICATION
# ============================================================

def detect_constellation_region(rgb):

    # Detect green pixels
    green_mask = detect_green_mask(rgb)

    # Convert mask to OpenCV format
    inpaint_mask = (
        green_mask.astype(np.uint8) * 255
    )

    # Reconstruct background underneath green markings
    reconstructed = cv2.inpaint(
        rgb,
        inpaint_mask,
        INPAINT_RADIUS,
        cv2.INPAINT_TELEA
    )

    # Convert reconstructed image to grayscale
    gray = cv2.cvtColor(
        reconstructed,
        cv2.COLOR_RGB2GRAY
    )

    # White background = inside desired constellation
    inside_boundary_mask = (
        gray >= WHITE_THRESHOLD
    )

    return inside_boundary_mask


# ============================================================
# PROCESS PDF PAGE
# ============================================================

def process_page(page):

    matrix = pymupdf.Matrix(
        DPI / 72,
        DPI / 72
    )

    pix = page.get_pixmap(
        matrix=matrix,
        alpha=False,
        colorspace=pymupdf.csRGB
    )

    rgb = np.frombuffer(
        pix.samples,
        dtype=np.uint8
    ).reshape(
        pix.height,
        pix.width,
        3
    ).copy()

    # Detect original green pixels
    green_mask = detect_green_mask(rgb)

    # Detect the desired constellation region
    inside_boundary_mask = detect_constellation_region(rgb)

    # Run original green removal function
    cleaned, removed, remaining, unchanged = remove_green(rgb)

    # Identify green pixels outside the constellation boundary
    outside_green = green_mask & ~inside_boundary_mask

    # Replace exterior green pixels with light grey
    cleaned[outside_green] = [222, 222, 222]

    # Count interior and exterior green pixels
    inside_green_pixels = int(
        np.count_nonzero(green_mask & inside_boundary_mask)
    )

    outside_green_pixels = int(
        np.count_nonzero(outside_green)
    )

    return (
        Image.fromarray(cleaned),
        removed,
        remaining,
        unchanged,
        inside_green_pixels,
        outside_green_pixels
    )


# ============================================================
# PROCESS ONE PDF
# ============================================================

def process_pdf(input_path):

    print()
    print("=" * 65)
    print(f"PROCESSING: {input_path.name}")
    print("=" * 65)

    doc = pymupdf.open(input_path)

    new_doc = pymupdf.open()

    output_pdf = OUTPUT_DIR / f"{input_path.stem}_processed.pdf"

    output_jpg = OUTPUT_DIR / f"{input_path.stem}_processed.jpg"

    total_removed = 0
    total_remaining = 0

    total_inside = 0
    total_outside = 0

    all_unchanged = True

    first_page = True

    try:

        for page_number, page in enumerate(doc, start=1):

            (
                cleaned,
                removed,
                remaining,
                unchanged,
                inside_pixels,
                outside_pixels
            ) = process_page(page)

            total_removed += removed
            total_remaining += remaining

            total_inside += inside_pixels
            total_outside += outside_pixels

            all_unchanged = all_unchanged and unchanged

            # Save first page as JPEG preview
            if first_page:

                cleaned.save(
                    output_jpg,
                    format="JPEG",
                    quality=JPEG_QUALITY,
                    optimize=True
                )

                first_page = False

            # Add cleaned image to output PDF
            buffer = io.BytesIO()

            cleaned.save(
                buffer,
                format="PNG"
            )

            new_page = new_doc.new_page(
                width=page.rect.width,
                height=page.rect.height
            )

            new_page.insert_image(
                new_page.rect,
                stream=buffer.getvalue()
            )

            print(f"\nPage {page_number}")
            print(f"  Green pixels detected : {removed:,}")
            print(f"  Interior green pixels : {inside_pixels:,}")
            print(f"  Exterior green pixels : {outside_pixels:,}")
            print(f"  Green pixels remaining: {remaining:,}")
            print(f"  Other pixels unchanged: {unchanged}")

        new_doc.save(
            output_pdf,
            garbage=4,
            deflate=True
        )

    finally:

        new_doc.close()
        doc.close()

    print("\nRESULT")
    print(f"  Total green pixels detected: {total_removed:,}")
    print(f"  Interior green pixels:       {total_inside:,}")
    print(f"  Exterior green pixels:       {total_outside:,}")
    print(f"  Remaining green pixels:      {total_remaining:,}")
    print(f"  Non-green pixels preserved:  {all_unchanged}")
    print(f"  PDF: {output_pdf}")
    print(f"  JPG: {output_jpg}")

    return {
        "file": input_path.name,
        "green_pixels_detected": total_removed,
        "interior_green_pixels": total_inside,
        "exterior_green_pixels": total_outside,
        "green_pixels_remaining": total_remaining,
        "non_masked_pixels_unchanged": all_unchanged,
        "needs_review": (
            total_remaining > 25 or
            not all_unchanged
        )
    }


# ============================================================
# STEP 3: CROP FINAL JPEG FILES
# EXACT ORIGINAL CROPPING LOGIC
# ============================================================

def crop_jpegs():

    folder = str(OUTPUT_DIR)

    # --------------------------------------------------------
    # SETTINGS
    # --------------------------------------------------------

    threshold = 245
    margin = 15

    # --------------------------------------------------------
    # PROCESS ALL JPG FILES
    # --------------------------------------------------------

    for filename in os.listdir(folder):

        if not filename.lower().endswith((".jpg", ".jpeg")):
            continue

        path = os.path.join(folder, filename)

        print(f"Processing: {filename}")

        # ----------------------------------------------------
        # LOAD IMAGE
        # ----------------------------------------------------

        img = cv2.imread(path)

        if img is None:
            print(f"  Could not read {filename}")
            continue

        h, w = img.shape[:2]

        # ----------------------------------------------------
        # FIND NON-WHITE PIXELS
        # ----------------------------------------------------

        gray = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2GRAY
        )

        # Pixels darker than threshold
        mask = gray < threshold

        ys, xs = np.where(mask)

        if len(xs) == 0:
            print("  No content detected, skipping.")
            continue

        # ----------------------------------------------------
        # BOUNDING BOX
        # ----------------------------------------------------

        left = xs.min()
        right = xs.max()
        top = ys.min()
        bottom = ys.max()

        # ----------------------------------------------------
        # ADD MARGIN
        # ----------------------------------------------------

        left = max(
            0,
            left - margin
        )

        top = max(
            0,
            top - margin
        )

        right = min(
            w,
            right + margin
        )

        bottom = min(
            h,
            bottom + margin
        )

        # ----------------------------------------------------
        # CROP
        # ----------------------------------------------------

        cropped = img[
            top:bottom,
            left:right
        ]

        # ----------------------------------------------------
        # OVERWRITE ORIGINAL
        # ----------------------------------------------------

        success = cv2.imwrite(
            path,
            cropped,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                95
            ]
        )

        if success:
            print(
                f"  {w}x{h} -> "
                f"{cropped.shape[1]}x{cropped.shape[0]}"
            )
        else:
            print(
                f"  Failed to save {filename}"
            )

    print("\nDone.")


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 65)
    print("IAU CONSTELLATION PDF PROCESSOR")
    print("=" * 65)

    print(f"\nOriginal PDFs: {SOURCE_DIR}")
    print(f"Text-removed PDFs: {TEXT_REMOVED_DIR}")
    print(f"Final output: {OUTPUT_DIR}")

    # --------------------------------------------------------
    # STEP 1: TEXT REMOVAL
    # --------------------------------------------------------

    pdf_files = sorted(
        SOURCE_DIR.glob("*.pdf")
    )

    if not pdf_files:

        print("\nNo original PDFs found.")
        return

    print(f"\nPDFs found: {len(pdf_files)}")

    successful_text_removals = 0

    for pdf_path in pdf_files:

        if remove_text(pdf_path):
            successful_text_removals += 1

    print("\n" + "=" * 65)
    print("TEXT REMOVAL COMPLETE")
    print("=" * 65)

    print(f"Successful: {successful_text_removals}")
    print(f"Failed: {len(pdf_files) - successful_text_removals}")

    # --------------------------------------------------------
    # STEP 2: GREEN REMOVAL
    # --------------------------------------------------------

    processed_files = sorted(
        INPUT_DIR.glob("*.pdf")
    )

    if not processed_files:

        print("\nNo text-removed PDFs found.")
        return

    print("\n" + "=" * 65)
    print("IAU GREEN MARKING REMOVAL")
    print("=" * 65)

    print(f"\nFound {len(processed_files)} PDFs.")

    results = []

    for pdf in processed_files:

        try:

            result = process_pdf(pdf)

            results.append(result)

        except Exception as e:

            print(f"\nERROR processing {pdf.name}: {e}")

            results.append({
                "file": pdf.name,
                "error": str(e),
                "needs_review": True
            })

    # --------------------------------------------------------
    # SAVE QA REPORT
    # --------------------------------------------------------

    with open(QA_LOG_PATH, "w") as f:

        json.dump(
            results,
            f,
            indent=2
        )

    flagged = [
        r for r in results
        if r.get("needs_review")
    ]

    # --------------------------------------------------------
    # STEP 3: CROP FINAL JPEG PREVIEWS
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print("CROPPING FINAL JPEG PREVIEWS")
    print("=" * 65)

    crop_jpegs()

    # --------------------------------------------------------
    # FINAL REPORT
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print("ALL PROCESSING COMPLETE")
    print("=" * 65)

    print(f"Text removal successful: {successful_text_removals}")
    print(f"Green processing completed: {len(results)}")
    print(f"Flagged for review: {len(flagged)}")

    print(f"\nText-removed PDFs: {TEXT_REMOVED_DIR}")
    print(f"Processed PDFs and JPEGs: {OUTPUT_DIR}")
    print(f"QA report: {QA_LOG_PATH}")


if __name__ == "__main__":
    main()
