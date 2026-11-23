
#!/usr/bin/env python3
"""
AstroTrainer — Wikimedia Commons Real-Sky Downloader

Downloads NOIRLab constellation images from Wikimedia Commons:
- Annotated images -> public/images/constellations/real-sky/annotated/
- Unannotated images -> public/images/constellations/real-sky/unannotated/

Features:
- Uses Wikimedia thumbnail URLs instead of repeatedly requesting originals.
- Downloads sequentially and respects Retry-After on HTTP 429.
- Retries temporary network/server errors with exponential backoff.
- Resumes safely: existing WebP files are not overwritten.
- Converts images to WebP using high quality.
- Saves source and licensing information in credits.csv.
- Saves failures and a summary in download_report.txt.

Install:
    python3 -m pip install requests pillow

Run from the AstroTrainer project root:
    python3 scripts/download_real_sky.py
"""

from __future__ import annotations

import csv
import html
import os
import re
import sys
import time
import random
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests
from PIL import Image, ImageOps, UnidentifiedImageError


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

BASE_DIR = (
    PROJECT_DIR
    / "public"
    / "images"
    / "constellations"
    / "real-sky"
)

UNANNOTATED_DIR = BASE_DIR / "unannotated"
ANNOTATED_DIR = BASE_DIR / "annotated"

CATEGORY = "Category:NOIRLab_images_of_constellation"

API_URL = "https://commons.wikimedia.org/w/api.php"

# Request a thumbnail rather than the original full-size file.
THUMBNAIL_WIDTH = 1920

# Be considerate to Wikimedia's servers.
DOWNLOAD_DELAY_SECONDS = 5.0
API_DELAY_SECONDS = 1.5

# Retry settings.
MAX_RETRIES = 4
BACKOFF_BASE_SECONDS = 30
MAX_BACKOFF_SECONDS = 300

# WebP settings.
WEBP_QUALITY = 95
WEBP_METHOD = 6
WEBP_LOSSLESS = False

# If False, existing files are preserved.
OVERWRITE_EXISTING = False

# Search subcategories too.
SEARCH_SUBCATEGORIES = True
MAX_CATEGORY_DEPTH = 3

# A descriptive User-Agent is important for Wikimedia.
USER_AGENT = (
    "AstroTrainerRealSkyDownloader/1.0 "
    "(educational astronomy project; Python requests)"
)

# ============================================================
# CONSTELLATIONS
# ============================================================

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
    "Hydrus": "hyd",
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

# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()
session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
})


def retry_after_seconds(response: requests.Response | None) -> float | None:
    """Read Retry-After as either seconds or an HTTP date."""
    if response is None:
        return None

    value = response.headers.get("Retry-After")
    if not value:
        return None

    try:
        return max(0.0, float(value))
    except ValueError:
        pass

    try:
        retry_date = parsedate_to_datetime(value)
        if retry_date.tzinfo is None:
            retry_date = retry_date.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        return max(0.0, (retry_date - now).total_seconds())
    except (TypeError, ValueError, OverflowError):
        return None


def request_with_retries(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    stream: bool = False,
    description: str = "request",
) -> requests.Response | None:
    """
    Make a request with controlled retries.

    429: respect Retry-After, otherwise use exponential backoff.
    5xx/timeouts: retry.
    403 and other permanent 4xx errors: do not repeatedly retry.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        response = None

        try:
            response = session.get(
                url,
                params=params,
                stream=stream,
                timeout=(20, 90),
            )

            if response.status_code == 429:
                wait = retry_after_seconds(response)

                if wait is None:
                    wait = min(
                        BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)),
                        MAX_BACKOFF_SECONDS,
                    )

                wait += random.uniform(1, 5)

                print(
                    f"\n  Rate limited (429) during {description}. "
                    f"Waiting {wait:.0f} seconds "
                    f"(attempt {attempt}/{MAX_RETRIES})..."
                )

                response.close()

                if attempt == MAX_RETRIES:
                    print("  Retry limit reached. Skipping this request.")
                    return None

                time.sleep(wait)
                continue

            if response.status_code in (500, 502, 503, 504):
                wait = min(
                    BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)),
                    MAX_BACKOFF_SECONDS,
                )
                wait += random.uniform(1, 5)

                print(
                    f"\n  Server error {response.status_code} during "
                    f"{description}. Waiting {wait:.0f} seconds..."
                )

                response.close()

                if attempt == MAX_RETRIES:
                    return None

                time.sleep(wait)
                continue

            if 400 <= response.status_code < 500:
                print(
                    f"\n  Permanent HTTP error {response.status_code} "
                    f"during {description}: {response.url}"
                )
                response.close()
                return None

            response.raise_for_status()
            return response

        except (requests.Timeout, requests.ConnectionError) as exc:
            if response is not None:
                response.close()

            wait = min(
                BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)),
                MAX_BACKOFF_SECONDS,
            )

            print(
                f"\n  Network error during {description}: {exc}. "
                f"Waiting {wait:.0f} seconds..."
            )

            if attempt == MAX_RETRIES:
                return None

            time.sleep(wait)

        except requests.RequestException as exc:
            if response is not None:
                response.close()

            print(f"\n  Request failed during {description}: {exc}")
            return None

    return None


# ============================================================
# TEXT / CONSTELLATION MATCHING
# ============================================================

def normalize_text(value: str) -> str:
    """Normalize punctuation and spacing for filename matching."""
    value = value.lower()
    value = re.sub(r"[_\-]+", " ", value)
    value = re.sub(r"[^a-z0-9 ]", " ", value)
    return " ".join(value.split())


NORMALIZED_CONSTELLATIONS = {
    name: normalize_text(name)
    for name in CONSTELLATIONS
}


def identify_constellation(title: str) -> tuple[str, str] | None:
    """
    Identify a constellation using whole-word phrase matching.

    This avoids matching short names such as Ara inside unrelated words.
    """
    normalized_title = f" {normalize_text(title)} "

    matches = []

    for name, normalized_name in NORMALIZED_CONSTELLATIONS.items():
        phrase = f" {normalized_name} "

        if phrase in normalized_title:
            matches.append((len(normalized_name), name))

    if not matches:
        return None

    # Prefer the longest matching constellation name.
    matches.sort(reverse=True)

    constellation_name = matches[0][1]
    abbreviation = CONSTELLATIONS[constellation_name]

    return constellation_name, abbreviation


def is_annotated(title: str) -> bool:
    """Classify files whose titles indicate constellation annotations."""
    normalized = normalize_text(title)

    annotation_terms = (
        "annotated",
        "annotation",
        "with constellation lines",
        "constellation lines",
        "with labels",
        "labelled",
        "labeled",
        "star names",
    )

    return any(term in normalized for term in annotation_terms)


# ============================================================
# WIKIMEDIA CATEGORY DISCOVERY
# ============================================================

def fetch_category_members(
    category: str,
) -> list[dict[str, Any]]:
    """Fetch files and, optionally, subcategories from Commons."""
    print(f"\nInspecting Wikimedia category: {category}")

    queue: list[tuple[str, int]] = [(category, 0)]
    visited_categories: set[str] = set()
    files: dict[str, dict[str, Any]] = {}

    while queue:
        current_category, depth = queue.pop(0)

        if current_category in visited_categories:
            continue

        visited_categories.add(current_category)

        continuation: dict[str, Any] = {}

        while True:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": current_category,
                "cmtype": "file|subcat" if SEARCH_SUBCATEGORIES else "file",
                "cmlimit": "max",
                "format": "json",
                "formatversion": "2",
                "maxlag": "5",
                **continuation,
            }

            response = request_with_retries(
                API_URL,
                params=params,
                description=f"category lookup: {current_category}",
            )

            if response is None:
                print(f"  Could not read category: {current_category}")
                break

            try:
                data = response.json()
            except ValueError:
                print("  Wikimedia returned invalid JSON.")
                response.close()
                break

            response.close()

            members = (
                data.get("query", {})
                .get("categorymembers", [])
            )

            for member in members:
                title = member.get("title", "")
                namespace = member.get("ns")

                if namespace == 6:
                    files[title] = member

                elif (
                    namespace == 14
                    and SEARCH_SUBCATEGORIES
                    and depth < MAX_CATEGORY_DEPTH
                ):
                    queue.append((title, depth + 1))

            next_continuation = data.get("continue")

            if not next_continuation:
                break

            continuation = next_continuation
            time.sleep(API_DELAY_SECONDS)

        time.sleep(API_DELAY_SECONDS)

    result = list(files.values())

    print(f"Found {len(result)} image files across {len(visited_categories)} categories.")
    return result


# ============================================================
# IMAGE INFORMATION / THUMBNAILS
# ============================================================

def fetch_image_information(
    file_members: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Fetch thumbnail URLs and licensing metadata in batches.

    iiurlwidth asks Wikimedia to provide a thumbnail URL.
    We prefer thumburl over the original url.
    """
    print("\nFetching image information and thumbnail URLs...")

    results: list[dict[str, Any]] = []
    batch_size = 50

    for start in range(0, len(file_members), batch_size):
        batch = file_members[start:start + batch_size]
        titles = [item["title"] for item in batch]

        params = {
            "action": "query",
            "titles": "|".join(titles),
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": str(THUMBNAIL_WIDTH),
            "format": "json",
            "formatversion": "2",
            "maxlag": "5",
        }

        response = request_with_retries(
            API_URL,
            params=params,
            description="image information lookup",
        )

        if response is None:
            print(f"  Skipping metadata batch beginning at item {start + 1}.")
            continue

        try:
            data = response.json()
        except ValueError:
            print("  Invalid JSON in image information response.")
            response.close()
            continue

        response.close()

        pages = data.get("query", {}).get("pages", [])

        # formatversion=2 normally returns a list.
        # This also tolerates dictionary-shaped responses.
        if isinstance(pages, dict):
            pages = list(pages.values())

        for page in pages:
            title = page.get("title", "")
            imageinfo_list = page.get("imageinfo", [])

            if not imageinfo_list:
                continue

            info = imageinfo_list[0]

            # Prefer the thumbnail URL.
            image_url = info.get("thumburl") or info.get("url")

            if not image_url:
                continue

            mime = info.get("mime", "")

            if not mime.startswith("image/"):
                continue

            results.append({
                "title": title,
                "url": image_url,
                "original_url": info.get("url", ""),
                "mime": mime,
                "width": info.get("thumbwidth", info.get("width", 0)),
                "height": info.get("thumbheight", info.get("height", 0)),
                "original_width": info.get("width", 0),
                "original_height": info.get("height", 0),
                "original_size": info.get("size", 0),
                "metadata": info.get("extmetadata", {}),
            })

        print(
            f"  Processed {min(start + batch_size, len(file_members))}"
            f"/{len(file_members)} files"
        )

        time.sleep(API_DELAY_SECONDS)

    print(f"Retrieved information for {len(results)} usable images.")
    return results


# ============================================================
# METADATA / ATTRIBUTION
# ============================================================

def metadata_value(metadata: dict[str, Any], key: str) -> str:
    """Extract readable text from Wikimedia extmetadata."""
    item = metadata.get(key, {})

    if isinstance(item, dict):
        value = item.get("value", "")
    else:
        value = str(item)

    value = re.sub(r"<[^>]+>", "", str(value))
    return html.unescape(value).strip()


def build_credit_record(
    item: dict[str, Any],
    output_path: Path,
    constellation: str,
    category_type: str,
) -> dict[str, str]:
    metadata = item.get("metadata", {})

    return {
        "output_file": str(output_path.relative_to(PROJECT_DIR)),
        "constellation": constellation,
        "type": category_type,
        "commons_title": item.get("title", ""),
        "source_url": item.get("original_url", ""),
        "thumbnail_url": item.get("url", ""),
        "artist": metadata_value(metadata, "Artist"),
        "credit": metadata_value(metadata, "Credit"),
        "license": metadata_value(metadata, "LicenseShortName"),
        "license_url": metadata_value(metadata, "LicenseUrl"),
        "description": metadata_value(metadata, "ImageDescription"),
    }


def save_credits(records: list[dict[str, str]]) -> None:
    credits_path = BASE_DIR / "credits.csv"

    if not records:
        return

    fieldnames = [
        "output_file",
        "constellation",
        "type",
        "commons_title",
        "source_url",
        "thumbnail_url",
        "artist",
        "credit",
        "license",
        "license_url",
        "description",
    ]

    # Preserve existing entries and update entries for the same output file.
    existing: dict[str, dict[str, str]] = {}

    if credits_path.exists():
        try:
            with credits_path.open(
                "r",
                newline="",
                encoding="utf-8-sig",
            ) as file:
                for row in csv.DictReader(file):
                    existing[row.get("output_file", "")] = row
        except OSError:
            pass

    for record in records:
        existing[record["output_file"]] = record

    with credits_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing.values())


# ============================================================
# DOWNLOAD AND WEBP CONVERSION
# ============================================================

def convert_download_to_webp(
    item: dict[str, Any],
    output_path: Path,
) -> tuple[bool, str]:
    """
    Download a thumbnail to a temporary file, validate it,
    then convert it to WebP.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    response = request_with_retries(
        item["url"],
        stream=True,
        description=f"image download: {item['title']}",
    )

    if response is None:
        return False, "Download request failed"

    source_temp_path: Path | None = None
    output_temp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".img",
            delete=False,
            dir=output_path.parent,
        ) as temp_file:
            source_temp_path = Path(temp_file.name)

            for chunk in response.iter_content(chunk_size=1024 * 128):
                if chunk:
                    temp_file.write(chunk)

        response.close()

        if (
            source_temp_path.stat().st_size < 100
        ):
            return False, "Downloaded file is unexpectedly small"

        with Image.open(source_temp_path) as source_image:
            source_image.load()

            image = ImageOps.exif_transpose(source_image)

            if image.mode not in ("RGB", "RGBA"):
                if "transparency" in image.info:
                    image = image.convert("RGBA")
                else:
                    image = image.convert("RGB")

            with tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=".webp",
                delete=False,
                dir=output_path.parent,
            ) as temp_output:
                output_temp_path = Path(temp_output.name)

            save_options = {
                "format": "WEBP",
                "method": WEBP_METHOD,
            }

            if WEBP_LOSSLESS:
                save_options["lossless"] = True
            else:
                save_options["quality"] = WEBP_QUALITY

            image.save(output_temp_path, **save_options)

        # Atomic replacement: a partially written output is never exposed.
        os.replace(output_temp_path, output_path)
        output_temp_path = None

        return True, "Downloaded and converted"

    except (
        OSError,
        ValueError,
        UnidentifiedImageError,
    ) as exc:
        return False, f"Image processing failed: {exc}"

    finally:
        response.close()

        if source_temp_path and source_temp_path.exists():
            source_temp_path.unlink(missing_ok=True)

        if output_temp_path and output_temp_path.exists():
            output_temp_path.unlink(missing_ok=True)


# ============================================================
# FILE SELECTION AND NAMING
# ============================================================

def group_images(
    image_items: list[dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """
    Group images by (constellation abbreviation, annotated/unannotated).
    """
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for item in image_items:
        match = identify_constellation(item["title"])

        if not match:
            continue

        constellation_name, abbreviation = match

        category_type = (
            "annotated" if is_annotated(item["title"])
            else "unannotated"
        )

        key = (abbreviation, category_type)

        item["constellation_name"] = constellation_name
        item["abbreviation"] = abbreviation
        item["category_type"] = category_type

        groups.setdefault(key, []).append(item)

    # Prefer larger source images for the primary file.
    for items in groups.values():
        items.sort(
            key=lambda item: (
                int(item.get("original_width") or 0)
                * int(item.get("original_height") or 0),
                int(item.get("original_size") or 0),
            ),
            reverse=True,
        )

    return groups


def output_filename(
    abbreviation: str,
    index: int,
) -> str:
    if index == 0:
        return f"{abbreviation}.webp"

    return f"{abbreviation}-{index + 1:02d}.webp"


# ============================================================
# REPORTING
# ============================================================

def write_report(
    lines: list[str],
    downloaded: int,
    skipped: int,
    failed: int,
    unmatched: int,
) -> None:
    report_path = BASE_DIR / "download_report.txt"

    summary = [
        "",
        "========================================",
        "ASTROTRAINER REAL-SKY DOWNLOAD REPORT",
        "========================================",
        f"Finished: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"Downloaded successfully: {downloaded}",
        f"Already existed / skipped: {skipped}",
        f"Failed: {failed}",
        f"Unmatched files: {unmatched}",
        "",
        "DETAILS",
        "----------------------------------------",
        *lines,
        "",
    ]

    report_path.write_text("\n".join(summary), encoding="utf-8")


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    UNANNOTATED_DIR.mkdir(parents=True, exist_ok=True)
    ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 64)
    print("ASTROTRAINER — REAL-SKY IMAGE DOWNLOADER")
    print("=" * 64)
    print(f"Project: {PROJECT_DIR}")
    print(f"Thumbnail width: {THUMBNAIL_WIDTH}px")
    print(f"WebP quality: {'lossless' if WEBP_LOSSLESS else WEBP_QUALITY}")
    print(f"Delay between image downloads: {DOWNLOAD_DELAY_SECONDS}s")
    print(f"Overwrite existing files: {OVERWRITE_EXISTING}")
    print()

    category_files = fetch_category_members(CATEGORY)

    if not category_files:
        print("\nNo files were found.")
        print(
            "Check the CATEGORY setting near the top of this script "
            "and confirm that the Commons category exists."
        )
        return

    image_items = fetch_image_information(category_files)

    if not image_items:
        print("\nNo usable image information was retrieved.")
        print("Try again later if Wikimedia is temporarily rate-limiting requests.")
        return

    groups = group_images(image_items)

    matched_titles = {
        item["title"]
        for items in groups.values()
        for item in items
    }

    unmatched = len(image_items) - len(matched_titles)

    print("\nImage groups found:")
    for (abbreviation, category_type), items in sorted(groups.items()):
        print(f"  {abbreviation.upper():3} | {category_type:12} | {len(items)} image(s)")

    print("\nStarting downloads...\n")

    downloaded = 0
    skipped = 0
    failed = 0

    report_lines: list[str] = []
    credit_records: list[dict[str, str]] = []

    total = sum(len(items) for items in groups.values())
    current = 0

    for (abbreviation, category_type), items in sorted(groups.items()):
        output_dir = (
            ANNOTATED_DIR
            if category_type == "annotated"
            else UNANNOTATED_DIR
        )

        constellation_name = items[0]["constellation_name"]

        print(
            f"\n{constellation_name} ({abbreviation.upper()}) "
            f"— {category_type}"
        )

        for index, item in enumerate(items):
            current += 1

            filename = output_filename(abbreviation, index)
            output_path = output_dir / filename

            print(
                f"  [{current}/{total}] "
                f"{item['title']}"
            )

            if output_path.exists() and not OVERWRITE_EXISTING:
                print(f"      SKIPPED — already exists: {filename}")
                skipped += 1

                credit_records.append(
                    build_credit_record(
                        item,
                        output_path,
                        constellation_name,
                        category_type,
                    )
                )

                report_lines.append(
                    f"SKIPPED | {category_type} | "
                    f"{constellation_name} | {filename} | already exists"
                )
                continue

            success, message = convert_download_to_webp(
                item,
                output_path,
            )

            if success:
                downloaded += 1

                size_kb = output_path.stat().st_size / 1024

                print(
                    f"      OK — {filename} "
                    f"({size_kb:.1f} KB)"
                )

                credit_records.append(
                    build_credit_record(
                        item,
                        output_path,
                        constellation_name,
                        category_type,
                    )
                )

                report_lines.append(
                    f"OK | {category_type} | "
                    f"{constellation_name} | {filename} | "
                    f"{item['title']}"
                )

            else:
                failed += 1

                print(f"      FAILED — {message}")

                report_lines.append(
                    f"FAILED | {category_type} | "
                    f"{constellation_name} | {filename} | "
                    f"{message} | {item['url']}"
                )

            # Do not hammer Wikimedia's thumbnail server.
            time.sleep(DOWNLOAD_DELAY_SECONDS)

        # Save attribution as we go, so an interruption does not lose it.
        save_credits(credit_records)

    save_credits(credit_records)

    write_report(
        report_lines,
        downloaded,
        skipped,
        failed,
        unmatched,
    )

    print("\n" + "=" * 64)
    print("DOWNLOAD FINISHED")
    print("=" * 64)
    print(f"Downloaded: {downloaded}")
    print(f"Skipped:    {skipped}")
    print(f"Failed:     {failed}")
    print(f"Unmatched:  {unmatched}")
    print()
    print(f"Unannotated images: {UNANNOTATED_DIR}")
    print(f"Annotated images:   {ANNOTATED_DIR}")
    print(f"Credits:            {BASE_DIR / 'credits.csv'}")
    print(f"Report:             {BASE_DIR / 'download_report.txt'}")
    print()

    if failed:
        print(
            "Some downloads failed. You can run the script again later; "
            "successfully downloaded files will be skipped."
        )

    if unmatched:
        print(
            "Some files could not be matched to a constellation by title. "
            "They were not downloaded."
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Existing downloaded files are safe.")
        sys.exit(130)
