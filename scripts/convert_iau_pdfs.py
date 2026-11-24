
from pathlib import Path
import fitz  # PyMuPDF
import cv2
import numpy as np
import re

# ============================================================
# PATHS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT_DIR / "public" / "iau-constellations"
OUTPUT_DIR = INPUT_DIR / "annotated-webp"

# ============================================================
# SETTINGS
# ============================================================

THRESHOLD = 245
MARGIN = 15

WEBP_QUALITY = 90
RENDER_DPI = 200

# ============================================================
# HELPERS
# ============================================================

def clean_filename(name):
    name = re.sub(r"[^\w-]+", "-", name)
    return name.strip("-").lower()


def crop_content(img):
    h, w = img.shape[:2]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Same cropping logic as your previous script
    mask = gray < THRESHOLD

    ys, xs = np.where(mask)

    if len(xs) == 0:
        print("  No content detected. Keeping original dimensions.")
        return img

    left = max(0, xs.min() - MARGIN)
    right = min(w, xs.max() + MARGIN)

    top = max(0, ys.min() - MARGIN)
    bottom = min(h, ys.max() + MARGIN)

    return img[top:bottom, left:right]


# ============================================================
# PROCESS PDF
# ============================================================

def process_pdf(pdf_path):

    print(f"\nProcessing: {pdf_path.name}")

    try:
        document = fitz.open(pdf_path)
    except Exception as e:
        print(f"  Could not open PDF: {e}")
        return

    base_name = clean_filename(pdf_path.stem)

    for page_number, page in enumerate(document):

        print(f"  Rendering page {page_number + 1}/{len(document)}")

        # Render PDF page at high resolution
        pix = page.get_pixmap(
            dpi=RENDER_DPI,
            colorspace=fitz.csRGB,
            alpha=False
        )

        img = np.frombuffer(
            pix.samples,
            dtype=np.uint8
        ).reshape(
            pix.height,
            pix.width,
            3
        )

        # Convert RGB to OpenCV BGR
        img = cv2.cvtColor(
            img,
            cv2.COLOR_RGB2BGR
        )

        original_h, original_w = img.shape[:2]

        # Crop using the previous script's logic
        cropped = crop_content(img)

        # Output filename
        if len(document) == 1:
            output_name = f"{base_name}.webp"
        else:
            output_name = f"{base_name}-page-{page_number + 1}.webp"

        output_path = OUTPUT_DIR / output_name

        # Save as WebP
        success = cv2.imwrite(
            str(output_path),
            cropped,
            [
                cv2.IMWRITE_WEBP_QUALITY,
                WEBP_QUALITY
            ]
        )

        if success:
            new_h, new_w = cropped.shape[:2]

            print(
                f"  Saved: {output_name} | "
                f"{original_w}x{original_h} -> "
                f"{new_w}x{new_h}"
            )
        else:
            print(f"  Failed to save: {output_name}")

    document.close()


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    pdf_files = sorted(
        INPUT_DIR.glob("*.pdf")
    )

    if not pdf_files:
        print("No PDF files found.")
        return

    print("=" * 55)
    print("IAU CONSTELLATION PDF CONVERTER")
    print("=" * 55)

    print(f"Input:  {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"PDFs found: {len(pdf_files)}")

    for pdf_path in pdf_files:
        process_pdf(pdf_path)

    print("\n" + "=" * 55)
    print("CONVERSION COMPLETE")
    print("=" * 55)


if __name__ == "__main__":
    main()
