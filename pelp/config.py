"""
Central configuration for the DOE PELP scraper and API in PowerForecast.

Contains target URLs, category mappings, file paths, and fallback PDF URLs
in case the live page structure changes.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
DATA_DIR = PROJECT_ROOT / "pelp_data"
RAW_PDFS_DIR = DATA_DIR / "raw_pdfs"
PARSED_JSON_DIR = DATA_DIR / "parsed_json"

# Ensure directories exist at import time
RAW_PDFS_DIR.mkdir(parents=True, exist_ok=True)
PARSED_JSON_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Target page
# ---------------------------------------------------------------------------
DOE_PELP_URL = (
    "https://doe.gov.ph/articles/2837255--pelp-registration-and-energy-label-"
    "issuance-as-of-june-30-2025?title=PELP%20Registration%20and%20Energy%20"
    "Label%20Issuance%20as%20of%20June%2030,%202025"
)

# ---------------------------------------------------------------------------
# Category definitions
# ---------------------------------------------------------------------------
# Maps a human-readable category name -> API slug (used in URL paths and
# filenames). The scraper matches <a> tag text against the keys to locate
# the correct PDF download link on the page.
CATEGORIES: dict[str, str] = {
    "Air Conditioners": "air-conditioners",
    "Lighting Products": "lighting-products",
    "Refrigerating Appliances": "refrigerating-appliances",
    "Television Sets": "television-sets",
    "Electric Fans": "electric-fans",
    "Clothes Washing Machines": "clothes-washing-machines",
}

# Reverse lookup: slug -> display name
SLUG_TO_NAME: dict[str, str] = {v: k for k, v in CATEGORIES.items()}

# ---------------------------------------------------------------------------
# Fallback / hardcoded PDF URLs
# ---------------------------------------------------------------------------
# If the live page cannot be scraped (e.g. JS-rendered, layout change), we
# fall back to these known-good direct download URLs discovered on
# 2025-07-28.
FALLBACK_PDF_URLS: dict[str, str] = {
    "air-conditioners": (
        "https://prod-cms.doe.gov.ph/documents/d/guest/"
        "attachment-b-acu-el-as-of-june-30-2025-pdf"
    ),
    "lighting-products": (
        "https://prod-cms.doe.gov.ph/documents/d/guest/"
        "attachment-b-lp-el-as-of-june-30-2025-pdf"
    ),
    "refrigerating-appliances": (
        "https://prod-cms.doe.gov.ph/documents/d/guest/"
        "attachment-b-ref-el-as-of-june-30-2025-pdf"
    ),
    "television-sets": (
        "https://prod-cms.doe.gov.ph/documents/d/guest/"
        "attachment-b-tvl-el-as-of-june-30-2025-pdf"
    ),
    "electric-fans": (
        "https://prod-cms.doe.gov.ph/documents/d/guest/"
        "attachment-b-efu-el-as-of-june-30-2025-pdf"
    ),
    "clothes-washing-machines": (
        "https://prod-cms.doe.gov.ph/documents/d/guest/"
        "attachment-b-cwm-el-as-of-june-30-2025-pdf"
    ),
}

# ---------------------------------------------------------------------------
# Server settings
# ---------------------------------------------------------------------------
API_HOST = "127.0.0.1"
API_PORT = 8000
