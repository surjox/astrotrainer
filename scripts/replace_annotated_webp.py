
from pathlib import Path
import fitz
import cv2
import numpy as np

# ============================================================
# PATHS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

FOLDER = (
    PROJECT_DIR
    / "public"
    / "iau-constellations"
    / "text-removed"
)

# ============================================================
# SETTINGS
# ============================================================

THRESHOLD = 245
MARGIN = 15

WEBP_QUALITY = 90
RENDER_DPI = 200

# ============================================================
# CROP
# ============================================================

def crop_content(img):

    h, w = img.shape[:2]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = gray < THRESHOLD

    ys, xs = np.where(mask)

    if len(xs) == 0:
        return img

    left = max(0, xs.min() - MARGIN)
    right = min(w, xs.max() + MARGIN)

    top = max(0, ys.min() - MARGIN)
    bottom = min(h, ys.max() + MARGIN)

    return img[top:bottom, left:right]


# ============================================================
# CONVERT
# ============================================================

def convert_pdf(pdf_path):

    print(f"\nProcessing: {pdf_path.name}")

    doc = fitz.open(pdf_path)
    outputs = []

    try:
        for page_number, page in enumerate(doc):

            pix = page.get_pixmap(
                dpi=RENDER_DPI,
                colorspace=fitz.csRGB,
                alpha=False
            )

            img = np.frombuffer(
                pix.samples,
                dtype=np.uint8
            ).reshape(pix.height, pix.width, 3)

            img = cv2.cvtColor(
                img,
                cv2.COLOR_RGB2BGR
            )

            cropped = crop_content(img)

            if len(doc) == 1:
                filename = f"{pdf_path.stem}.webp"
            else:
                filename = (
                    f"{pdf_path.stem}-page-{page_number + 1}.webp"
                )

            output_path = FOLDER / filename

            success = cv2.imwrite(
                str(output_path),
                cropped,
                [
                    cv2.IMWRITE_WEBP_QUALITY,
                    WEBP_QUALITY
                ]
            )

            if not success:
                raise RuntimeError(
                    f"Failed to save {filename}"
                )

            outputs.append(output_path)

            print(f"  Saved: {filename}")

    except Exception as e:

        print(f"  ERROR: {e}")

        # Remove incomplete outputs from this PDF
        for output in outputs:
            output.unlink(missing_ok=True)

        doc.close()
        return

    doc.close()

    # Delete PDF only after all pages were converted
    pdf_path.unlink()

    print("  Original PDF removed.")


# ============================================================
# MAIN
# ============================================================

def main():

    pdf_files = sorted(FOLDER.glob("*.pdf"))

    if not pdf_files:
        print("No PDFs found.")
        return

    print(f"Found {len(pdf_files)} PDFs.")

    for pdf_path in pdf_files:
        convert_pdf(pdf_path)

    print("\nConversion complete!")


if __name__ == "__main__":
    main()
