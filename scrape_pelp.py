"""
DOE PELP Scraping & Parsing CLI tool.

Usage:
    python scrape_pelp.py
    python scrape_pelp.py --force
    python scrape_pelp.py --parse-only
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from pelp.scraper import run_scrape_and_download
from pelp.parser import parse_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger("scrape_pelp")


def main():
    parser = argparse.ArgumentParser(description="DOE PELP Scraper & Parser Pipeline")
    parser.add_argument("--force", action="store_true", help="Re-download PDFs even if cached")
    parser.add_argument("--parse-only", action="store_true", help="Skip download and re-parse existing PDFs in pelp_data/raw_pdfs")
    args = parser.parse_args()

    if not args.parse_only:
        logger.info("Starting PDF download pipeline (force=%s)...", args.force)
        downloaded = run_scrape_and_download(force=args.force)
        logger.info("Downloaded / verified %d PDFs.", len(downloaded))

    logger.info("Parsing PDF tables into JSON...")
    results = parse_all()
    total = sum(len(rows) for rows in results.values())
    logger.info("Extraction complete: %d total products across %d categories.", total, len(results))
    for slug, rows in results.items():
        logger.info("  • %-30s : %d products", slug, len(rows))


if __name__ == "__main__":
    main()
