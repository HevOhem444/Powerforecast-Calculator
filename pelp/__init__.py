"""
DOE PELP (Philippine Energy Labeling Program) Scraping & Parsing Package.
Provides automated pipeline to scrape DOE PDF registrations and extract structured JSON datasets.
"""

from .config import (
    CATEGORIES,
    SLUG_TO_NAME,
    FALLBACK_PDF_URLS,
    DATA_DIR,
    RAW_PDFS_DIR,
    PARSED_JSON_DIR,
)
from .models import (
    ApplianceProduct,
    CategorySummary,
    CategoryResponse,
    AllAppliancesResponse,
    SearchResponse,
    ScrapeResult,
)
from .scraper import scrape_pdf_links, download_pdfs, run_scrape_and_download
from .parser import parse_pdf, parse_all, load_parsed_data

__all__ = [
    "CATEGORIES",
    "SLUG_TO_NAME",
    "FALLBACK_PDF_URLS",
    "DATA_DIR",
    "RAW_PDFS_DIR",
    "PARSED_JSON_DIR",
    "ApplianceProduct",
    "CategorySummary",
    "CategoryResponse",
    "AllAppliancesResponse",
    "SearchResponse",
    "ScrapeResult",
    "scrape_pdf_links",
    "download_pdfs",
    "run_scrape_and_download",
    "parse_pdf",
    "parse_all",
    "load_parsed_data",
]
