
from pathlib import Path
import shutil

# Exact folder paths
source = Path.home() / "documents/codes/public/messier"

destination = (
    Path.home() / "Documents/astrotrainer/public/messier"
)

extensions = {".webp", ".png", ".jpg", ".jpeg"}

if not source.exists():
    raise FileNotFoundError(f"Source not found: {source}")

if not destination.exists():
    raise FileNotFoundError(f"Destination not found: {destination}")

copied = 0
skipped = 0

print("Starting safe image merge...\n")

for source_folder in sorted(source.iterdir()):

    if not source_folder.is_dir():
        continue

    messier = source_folder.name.upper()

    if not messier.startswith("M") or not messier[1:].isdigit():
        continue

    dest_folder = destination / messier
    dest_folder.mkdir(exist_ok=True)

    images = sorted([
        f for f in source_folder.rglob("*")
        if f.is_file() and f.suffix.lower() in extensions
    ])

    for image in images:

        # Preserve relative subfolder structure if present
        relative_path = image.relative_to(source_folder)
        target = dest_folder / relative_path

        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():

            # Skip identical images
            if (
                target.stat().st_size == image.stat().st_size
                and target.read_bytes() == image.read_bytes()
            ):
                print(f"[SKIP] {messier}/{relative_path}")
                skipped += 1
                continue

            # Find an unused numbered filename
            index = 1

            while True:
                new_name = f"{index:02d}{image.suffix.lower()}"
                alternative = target.parent / new_name

                if not alternative.exists():
                    target = alternative
                    break

                index += 1

        shutil.copy2(image, target)

        copied += 1
        print(f"[COPIED] {messier}/{target.name}")

print("\n========== MERGE COMPLETE ==========")
print(f"Images copied: {copied}")
print(f"Duplicates skipped: {skipped}")
print("Existing AstroTrainer images were preserved.")
