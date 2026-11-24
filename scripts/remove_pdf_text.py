
from pathlib import Path
import fitz

# ============================================================
# PATHS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT_DIR / "public" / "iau-constellations"
OUTPUT_DIR = INPUT_DIR / "text-removed"

# ============================================================
# PROCESS PDF
# ============================================================

def remove_text(pdf_path):

    print(f"\nProcessing: {pdf_path.name}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"  Could not open PDF: {e}")
        return

    total_spans = 0

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
    output_path = OUTPUT_DIR / pdf_path.name

    try:
        doc.save(
            str(output_path),
            garbage=4,
            deflate=True
        )

        print(f"  Text spans removed: {total_spans}")
        print(f"  Saved: {output_path.name}")

    except Exception as e:
        print(f"  Save failed: {e}")

    doc.close()


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDFs found.")
        return

    print("=" * 55)
    print("PDF SELECTABLE TEXT REMOVER")
    print("=" * 55)

    print(f"PDFs found: {len(pdf_files)}")

    for pdf_path in pdf_files:
        remove_text(pdf_path)

    print("\n" + "=" * 55)
    print("PROCESSING COMPLETE")
    print("=" * 55)


if __name__ == "__main__":
    main()
