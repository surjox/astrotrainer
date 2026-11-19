
from PIL import Image
from pathlib import Path

folder = Path("Messier Objects").resolve()
quality = 85

print(f"Searching in: {folder}")

if not folder.exists():
    print("ERROR: Folder does not exist!")
    exit()

png_files = list(folder.glob("*.png"))

print(f"Found {len(png_files)} PNG files.\n")

converted = 0

for png_file in png_files:
    try:
        with Image.open(png_file) as img:
            webp_file = png_file.with_suffix(".webp")

            img.save(
                webp_file,
                "WEBP",
                quality=quality,
                method=6
            )

        converted += 1
        print(f"Converted: {png_file.name}")

    except Exception as e:
        print(f"Failed: {png_file.name} | {e}")

print(f"\nConversion complete! {converted}/{len(png_files)} files converted.")
