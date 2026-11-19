
from pathlib import Path

folder = Path("Messier Objects").resolve()

png_files = list(folder.rglob("*.png"))

for png_file in png_files:
    png_file.unlink()
    print(f"Deleted: {png_file.name}")

print(f"\nDeleted {len(png_files)} PNG files.")
