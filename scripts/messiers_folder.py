
from pathlib import Path
import shutil
import re

folder = Path("public/messier").resolve()

extensions = {".webp", ".png", ".jpg", ".jpeg"}
pattern = re.compile(r"^(M\d+)", re.IGNORECASE)

# Collect all images recursively
images = [
    p for p in folder.rglob("*")
    if p.is_file() and p.suffix.lower() in extensions
]

# Group images by Messier designation
groups = {}

for image in images:
    match = pattern.match(image.stem)

    if match:
        messier = match.group(1).upper()
        groups.setdefault(messier, []).append(image)
    else:
        print(f"Skipped: {image}")

# Process each Messier object
for messier, files in sorted(groups.items()):

    destination = folder / messier
    destination.mkdir(exist_ok=True)

    # Sort by filename
    files.sort(key=lambda p: p.name.lower())

    # Move images to unique temporary files first
    temp_files = []

    for index, image in enumerate(files, start=1):
        temp = folder / f"__temp_{messier}_{index}{image.suffix.lower()}"

        while temp.exists():
            temp = folder / f"__temp_{messier}_{index}_x{image.suffix.lower()}"

        shutil.move(str(image), str(temp))
        temp_files.append(temp)

    # Rename and move into destination folder
    for index, temp in enumerate(temp_files, start=1):

        new_path = destination / f"{index:02d}{temp.suffix.lower()}"

        shutil.move(str(temp), str(new_path))

        print(f"Moved: {messier}/{new_path.name}")

    print(f"Completed {messier}: {len(files)} images\n")

print("All Messier images organized successfully!")
