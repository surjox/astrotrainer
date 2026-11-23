
import csv
import re
import time
import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from playwright.sync_api import sync_playwright

# ============================================================
# CONFIGURATION
# ============================================================

START_URL = "https://noirlab.edu/public/education/constellations/"

OUTPUT_DIR = Path.home() / "Desktop" / "NOIRLab_88_Constellations"

ANNOTATED_DIR = OUTPUT_DIR / "annotated"
UNANNOTATED_DIR = OUTPUT_DIR / "unannotated"
UNKNOWN_DIR = OUTPUT_DIR / "needs_review"

REPORT_PATH = OUTPUT_DIR / "download_report.csv"

ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)
UNANNOTATED_DIR.mkdir(parents=True, exist_ok=True)
UNKNOWN_DIR.mkdir(parents=True, exist_ok=True)

HEADLESS = False
DELAY_BETWEEN_DOWNLOADS = 1.0

# Official IAU abbreviations
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

IMAGE_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"
)

# ============================================================
# HELPERS
# ============================================================

def normalize(text):
    text = (text or "").lower()
    text = text.replace("ö", "o")
    text = text.replace("æ", "ae")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def identify_constellation(text):
    normalized = normalize(text)

    matches = []

    for name, abbreviation in CONSTELLATIONS.items():
        candidate = normalize(name)

        if candidate in normalized:
            matches.append((len(candidate), name, abbreviation))

    if not matches:
        return None, None

    # Prefer the longest match to avoid matching Leo inside Leo Minor.
    matches.sort(reverse=True)

    return matches[0][1], matches[0][2]


def clean_url(url):
    if not url:
        return None

    url = urljoin(START_URL, url)
    url, _ = urldefrag(url)

    if not url.startswith(("http://", "https://")):
        return None

    return url


def is_image_url(url):
    path = urlparse(url).path.lower()

    return (
        path.endswith(IMAGE_EXTENSIONS)
        or "/media/archives/images/" in path
    )


def classify_image(description, url):
    """
    Return annotated, unannotated, or unknown.
    Never guess when the available evidence is ambiguous.
    """

    text = normalize(description + " " + url)

    annotated_markers = [
        "annotated",
        "annotation",
        "with constellation lines",
        "with labels",
        "labelled",
        "labeled",
        "constellation figures",
    ]

    unannotated_markers = [
        "unannotated",
        "unlabelled",
        "unlabeled",
        "without labels",
        "without constellation lines",
        "no labels",
    ]

    if any(marker in text for marker in unannotated_markers):
        return "unannotated"

    if any(marker in text for marker in annotated_markers):
        return "annotated"

    return "unknown"


def unique_filename(directory, abbreviation, extension):
    extension = extension.lower()

    if extension == ".jpeg":
        extension = ".jpg"

    index = 1

    while True:
        if index == 1:
            filename = f"{abbreviation}{extension}"
        else:
            filename = f"{abbreviation}-{index:02d}{extension}"

        path = directory / filename

        if not path.exists():
            return path

        index += 1


def download_image(session, url, destination):
    try:
        response = session.get(
            url,
            timeout=90,
            stream=True,
            headers={
                "User-Agent": "Mozilla/5.0 AstroTrainer educational image collector"
            },
        )

        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()

        if "image" not in content_type:
            print(f"  SKIPPED: Not an image response: {content_type}")
            return False

        with open(destination, "wb") as file:
            for chunk in response.iter_content(1024 * 256):
                if chunk:
                    file.write(chunk)

        if destination.stat().st_size < 10_000:
            destination.unlink(missing_ok=True)
            print("  SKIPPED: File unexpectedly small")
            return False

        return True

    except Exception as error:
        print(f"  DOWNLOAD ERROR: {error}")
        destination.unlink(missing_ok=True)
        return False


# ============================================================
# PAGE EXTRACTION
# ============================================================

def extract_page_data(page, page_url):
    """
    Extract image URLs and their surrounding descriptions.
    Also extract links to other constellation pages.
    """

    return page.evaluate("""
    () => {
        const results = [];

        const add = (url, description) => {
            if (!url) return;

            results.push({
                url: url,
                description: description || ""
            });
        };

        // Direct links, including download buttons.
        document.querySelectorAll("a[href]").forEach(a => {
            const href = a.href;
            const context = [
                a.innerText,
                a.getAttribute("aria-label"),
                a.title,
                a.parentElement?.innerText
            ].filter(Boolean).join(" ");

            add(href, context);
        });

        // Images and their alternative sources.
        document.querySelectorAll("img").forEach(img => {
            const context = [
                img.alt,
                img.title,
                img.parentElement?.innerText
            ].filter(Boolean).join(" ");

            add(img.currentSrc || img.src, context);

            [
                "data-src",
                "data-original",
                "data-download",
                "data-url",
                "data-href"
            ].forEach(attribute => {
                add(img.getAttribute(attribute), context);
            });

            const srcset = img.getAttribute("srcset");

            if (srcset) {
                srcset.split(",").forEach(item => {
                    add(item.trim().split(/\\s+/)[0], context);
                });
            }
        });

        // Download-related data attributes on buttons and links.
        document.querySelectorAll(
            "a, button, [data-download], [data-url], [data-href]"
        ).forEach(element => {
            const context = [
                element.innerText,
                element.getAttribute("aria-label"),
                element.title
            ].filter(Boolean).join(" ");

            [
                "href",
                "data-download",
                "data-url",
                "data-href"
            ].forEach(attribute => {
                add(element.getAttribute(attribute), context);
            });
        });

        // Constellation page links.
        const pages = [];

        document.querySelectorAll("a[href]").forEach(a => {
            pages.push({
                url: a.href,
                text: [
                    a.innerText,
                    a.title,
                    a.getAttribute("aria-label")
                ].filter(Boolean).join(" ")
            });
        });

        return {
            images: results,
            pages: pages,
            title: document.title
        };
    }
    """)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 65)
    print("NOIRLab 88 Constellations Downloader")
    print("=" * 65)

    print(f"\nOutput directory: {OUTPUT_DIR}")
    print("\nOpening NOIRLab in Chromium...")

    discovered_pages = {}
    discovered_images = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=HEADLESS
        )

        page = browser.new_page(
            viewport={"width": 1440, "height": 1000}
        )

        page.goto(
            START_URL,
            wait_until="domcontentloaded",
            timeout=120000
        )

        print("\nIf NOIRLab displays a verification page,")
        print("complete it in the browser window.")
        input("When the constellation website is visible, press ENTER here...")

        page.wait_for_timeout(3000)

        # ----------------------------------------------------
        # Discover constellation pages from landing page
        # ----------------------------------------------------

        print("\nDiscovering constellation pages...")

        landing_data = extract_page_data(page, START_URL)

        for item in landing_data["pages"]:
            url = clean_url(item["url"])

            if not url:
                continue

            parsed = urlparse(url)

            if parsed.netloc != urlparse(START_URL).netloc:
                continue

            name, abbreviation = identify_constellation(
                item["text"] + " " + url
            )

            if name and url.rstrip("/") != START_URL.rstrip("/"):
                discovered_pages[name] = url

        print(f"Discovered {len(discovered_pages)} constellation pages.")

        # ----------------------------------------------------
        # Visit every discovered constellation page
        # ----------------------------------------------------

        all_candidates = []

        for index, (name, url) in enumerate(
            discovered_pages.items(), start=1
        ):
            print(f"\n[{index}/{len(discovered_pages)}] {name}")

            try:
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=90000
                )

                page.wait_for_timeout(1800)

                data = extract_page_data(page, url)

                for item in data["images"]:
                    image_url = clean_url(item["url"])

                    if not image_url or not is_image_url(image_url):
                        continue

                    key = image_url.split("?")[0]

                    if key in discovered_images:
                        continue

                    discovered_images[key] = True

                    all_candidates.append({
                        "constellation": name,
                        "abbreviation": CONSTELLATIONS[name],
                        "url": image_url,
                        "description": item["description"],
                    })

            except Exception as error:
                print(f"  PAGE ERROR: {error}")

        browser.close()

    # --------------------------------------------------------
    # Download images
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print(f"Found {len(all_candidates)} unique image candidates.")
    print("Starting downloads...")
    print("=" * 65)

    session = requests.Session()

    report_rows = []
    downloaded_hashes = set()

    for index, item in enumerate(all_candidates, start=1):
        name = item["constellation"]
        abbreviation = item["abbreviation"]
        url = item["url"]
        description = item["description"]

        category = classify_image(description, url)

        if category == "annotated":
            destination_dir = ANNOTATED_DIR
        elif category == "unannotated":
            destination_dir = UNANNOTATED_DIR
        else:
            destination_dir = UNKNOWN_DIR

        extension = Path(urlparse(url).path).suffix.lower()

        if extension not in IMAGE_EXTENSIONS:
            extension = ".jpg"

        destination = unique_filename(
            destination_dir,
            abbreviation,
            extension
        )

        print(
            f"\n[{index}/{len(all_candidates)}] "
            f"{name} | {category}"
        )

        success = download_image(
            session,
            url,
            destination
        )

        if success:
            digest = hashlib.sha256(destination.read_bytes()).hexdigest()

            if digest in downloaded_hashes:
                destination.unlink(missing_ok=True)
                status = "duplicate_content_skipped"
                print("  Duplicate image content; removed extra copy.")
            else:
                downloaded_hashes.add(digest)
                status = "downloaded"
                print(f"  Saved: {destination.name}")
        else:
            status = "failed"

        report_rows.append({
            "constellation": name,
            "iau_abbreviation": abbreviation,
            "category": category,
            "url": url,
            "local_file": str(destination) if status == "downloaded" else "",
            "status": status,
            "description": description,
        })

        time.sleep(DELAY_BETWEEN_DOWNLOADS)

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    with open(
        REPORT_PATH,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "constellation",
                "iau_abbreviation",
                "category",
                "url",
                "local_file",
                "status",
                "description",
            ]
        )

        writer.writeheader()
        writer.writerows(report_rows)

    successful = sum(
        row["status"] == "downloaded"
        for row in report_rows
    )

    print("\n" + "=" * 65)
    print("DOWNLOAD FINISHED")
    print("=" * 65)

    print(f"Constellation pages found: {len(discovered_pages)}")
    print(f"Image candidates found: {len(all_candidates)}")
    print(f"Successfully downloaded: {successful}")
    print(f"Report: {REPORT_PATH}")

    print("\nAnnotated images:", ANNOTATED_DIR)
    print("Unannotated images:", UNANNOTATED_DIR)
    print("Unclassified images:", UNKNOWN_DIR)

    print("\nCheck the CSV report for missing constellations or failed files.")


if __name__ == "__main__":
    main()
