
from pathlib import Path
import re

folder = Path("public/messier").resolve()

extensions = {".webp", ".png", ".jpg", ".jpeg"}

for messier_folder in sorted(folder.iterdir()):

    if not messier_folder.is_dir():
        continue

    # Collect images and sort by their current numerical names
    images = [
        f for f in messier_folder.iterdir()
        if f.is_file() and f.suffix.lower() in extensions
    ]

    images.sort(
        key=lambda f: (
            int(f.stem) if f.stem.isdigit() else float("inf"),
            f.name.lower()
        )
    )

    if not images:
        continue

    print(f"\nProcessing {messier_folder.name}...")

    # First rename to temporary names to avoid conflicts
    temp_files = []

    for index, image in enumerate(images, start=1):
        temp = messier_folder / f"__temp_{index}{image.suffix.lower()}"
        image.rename(temp)
        temp_files.append(temp)

    # Rename sequentially
    for index, temp in enumerate(temp_files, start=1):
        new_name = f"{index:02d}{temp.suffix.lower()}"
        new_path = messier_folder / new_name

        temp.rename(new_path)

        print(f"  {new_name}")

print("\nAll Messier folders renumbered successfully!")
