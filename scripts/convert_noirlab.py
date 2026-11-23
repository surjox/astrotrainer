
from pathlib import Path
from PIL import Image, ImageOps
import csv
import re

# ==================================================
# PATHS
# ==================================================

SOURCE_DIR = Path.home() / "Desktop" / "88 IAU Constellations"

OUTPUT_DIR = Path.home() / "Desktop" / "NOIRLab_Unannotated_WebP"

QUALITY = 95
METHOD = 6

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==================================================
# OFFICIAL IAU ABBREVIATIONS
# ==================================================

CONSTELLATIONS = {
    "Andromeda": "and",
    "Antlia": "ant",
    "Apus": "aps",
    "Aquarius": "aqr",
    "Aquila": "aql",
    "Ara": "ara",
    "Aries": "ari",
    "Auriga": "aur",
    "Bootes": "boo",
    "Caelum": "cae",
    "Camelopardalis": "cam",
    "Cancer": "cnc",
    "Canes Venatici": "cvn",
    "Canis Major": "cma",
    "Canis Minor": "cmi",
    "Capricornus": "cap",
    "Carina": "car",
    "Cassiopeia": "cas",
    "Centaurus": "cen",
    "Cepheus": "cep",
    "Cetus": "cet",
    "Chamaeleon": "cha",
    "Circinus": "cir",
    "Columba": "col",
    "Coma Berenices": "com",
    "Corona Australis": "cra",
    "Corona Borealis": "crb",
    "Corvus": "crv",
    "Crater": "crt",
    "Crux": "cru",
    "Cygnus": "cyg",
    "Delphinus": "del",
    "Dorado": "dor",
    "Draco": "dra",
    "Equuleus": "equ",
    "Eridanus": "eri",
    "Fornax": "for",
    "Gemini": "gem",
    "Grus": "gru",
    "Hercules": "her",
    "Horologium": "hor",
    "Hydra": "hya",
    "Hydrus": "hyi",
    "Indus": "ind",
    "Lacerta": "lac",
    "Leo": "leo",
    "Leo Minor": "lmi",
    "Lepus": "lep",
    "Libra": "lib",
    "Lupus": "lup",
    "Lynx": "lyn",
    "Lyra": "lyr",
    "Mensa": "men",
    "Microscopium": "mic",
    "Monoceros": "mon",
    "Musca": "mus",
    "Norma": "nor",
    "Octans": "oct",
    "Ophiuchus": "oph",
    "Orion": "ori",
    "Pavo": "pav",
    "Pegasus": "peg",
    "Perseus": "per",
    "Phoenix": "phe",
    "Pictor": "pic",
    "Pisces": "psc",
    "Piscis Austrinus": "psa",
    "Puppis": "pup",
    "Pyxis": "pyx",
    "Reticulum": "ret",
    "Sagitta": "sge",
    "Sagittarius": "sgr",
    "Scorpius": "sco",
    "Sculptor": "scl",
    "Scutum": "sct",
    "Serpens": "ser",
    "Sextans": "sex",
    "Taurus": "tau",
    "Telescopium": "tel",
    "Triangulum": "tri",
    "Triangulum Australe": "tra",
    "Tucana": "tuc",
    "Ursa Major": "uma",
    "Ursa Minor": "umi",
    "Vela": "vel",
    "Virgo": "vir",
    "Volans": "vol",
    "Vulpecula": "vul",
}

def normalize(name):
    name = name.lower().replace("ö", "o")
    return re.sub(r"[^a-z0-9]", "", name)

LOOKUP = {
    normalize(name): abbreviation
    for name, abbreviation in CONSTELLATIONS.items()
}

# ==================================================
# CONVERSION
# ==================================================

def main():

    if not SOURCE_DIR.exists():
        print(f"ERROR: Folder not found:\n{SOURCE_DIR}")
        return

    files = sorted(
        p for p in SOURCE_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in (".tif", ".tiff")
    )

    print("=" * 60)
    print("NOIRLab TIFF TO WEBP CONVERTER")
    print("=" * 60)
    print(f"Source: {SOURCE_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"TIFF files found: {len(files)}")
    print()

    report = []
    successful = 0
    skipped = 0
    failed = 0

    for index, source in enumerate(files, 1):

        abbreviation = LOOKUP.get(normalize(source.stem))

        if not abbreviation:
            print(f"[{index}] UNKNOWN: {source.name}")
            report.append({
                "source": source.name,
                "output": "",
                "status": "unknown_constellation"
            })
            skipped += 1
            continue

        destination = OUTPUT_DIR / f"{abbreviation}.webp"

        print(f"[{index}/{len(files)}] {source.name} -> {destination.name}")

        if destination.exists():
            print("   SKIPPED: Output already exists")
            report.append({
                "source": source.name,
                "output": str(destination),
                "status": "already_exists"
            })
            skipped += 1
            continue

        try:
            with Image.open(source) as original:

                image = ImageOps.exif_transpose(original)

                # Preserve transparency if present.
                if "A" in image.getbands():
                    image = image.convert("RGBA")
                else:
                    image = image.convert("RGB")

                options = {
                    "format": "WEBP",
                    "quality": QUALITY,
                    "method": METHOD,
                }

                icc = original.info.get("icc_profile")
                if icc:
                    options["icc_profile"] = icc

                image.save(destination, **options)

            source_size = source.stat().st_size / (1024 ** 2)
            output_size = destination.stat().st_size / (1024 ** 2)

            print(
                f"   SUCCESS: {source_size:.1f} MB -> "
                f"{output_size:.1f} MB"
            )

            report.append({
                "source": source.name,
                "output": str(destination),
                "status": "converted"
            })

            successful += 1

        except Exception as error:
            destination.unlink(missing_ok=True)
            print(f"   ERROR: {error}")

            report.append({
                "source": source.name,
                "output": str(destination),
                "status": f"error: {error}"
            })

            failed += 1

    # Save report
    report_path = OUTPUT_DIR / "conversion_report.csv"

    with open(report_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["source", "output", "status"]
        )
        writer.writeheader()
        writer.writerows(report)

    print("\n" + "=" * 60)
    print("CONVERSION COMPLETE")
    print("=" * 60)
    print(f"Converted: {successful}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print(f"Report: {report_path}")
    print("\nOriginal TIFF files remain untouched.")


if __name__ == "__main__":
    main()
