"""
Web scraper — discovers PDF links on the DOE PELP page and downloads them.

Strategy:
1. Fetch the HTML from the DOE page with httpx.
2. Parse with BeautifulSoup and search for <a> tags whose visible text
   matches one of the six appliance category names.
3. If the live scrape finds fewer than expected, supplement with the
   hardcoded fallback URLs from config.py.
4. Download each PDF to pelp_data/raw_pdfs/{slug}.pdf, skipping files that
   already exist on disk (caching).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import httpx
from bs4 import BeautifulSoup

from .config import (
    CATEGORIES,
    DOE_PELP_URL,
    FALLBACK_PDF_URLS,
    RAW_PDFS_DIR,
)

logger = logging.getLogger(__name__)

# Generous timeout — the DOE site can be slow.
_TIMEOUT = httpx.Timeout(60.0, connect=30.0)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
}


# ── PDF link discovery ────────────────────────────────────────────────────


def scrape_pdf_links(url: str = DOE_PELP_URL) -> Dict[str, str]:
    """
    Scrape the target DOE page and return a mapping of
    ``{category_slug: pdf_download_url}``.

    Falls back to hardcoded URLs for any category not found dynamically.
    """
    discovered: Dict[str, str] = {}

    try:
        logger.info("Fetching DOE page: %s", url)
        with httpx.Client(timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Walk all anchor tags and match link text to category names.
        for a_tag in soup.find_all("a", href=True):
            link_text = a_tag.get_text(strip=True)
            for cat_name, slug in CATEGORIES.items():
                if cat_name.lower() == link_text.lower():
                    href = a_tag["href"]
                    # Make relative URLs absolute
                    if href.startswith("/"):
                        href = f"https://doe.gov.ph{href}"
                    discovered[slug] = href
                    logger.info("Found link for %s -> %s", slug, href)
                    break

    except Exception:
        logger.warning(
            "Live scrape failed or incomplete — falling back to hardcoded URLs.",
            exc_info=True,
        )

    # Fill in any categories we didn't find dynamically.
    for slug, fallback_url in FALLBACK_PDF_URLS.items():
        if slug not in discovered:
            logger.info("Using fallback URL for %s", slug)
            discovered[slug] = fallback_url

    return discovered


# ── PDF downloading ───────────────────────────────────────────────────────


def download_pdfs(
    links: Dict[str, str],
    dest_dir: Path = RAW_PDFS_DIR,
    force: bool = False,
) -> List[Path]:
    """
    Download PDFs for each category.

    Parameters
    ----------
    links : dict
        ``{category_slug: pdf_url}``
    dest_dir : Path
        Directory to save PDF files into.
    force : bool
        If True, re-download even if the file already exists.

    Returns
    -------
    list[Path]
        Paths to all downloaded (or cached) PDF files.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    downloaded: List[Path] = []

    with httpx.Client(timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True) as client:
        for slug, url in links.items():
            filepath = dest_dir / f"{slug}.pdf"

            if filepath.exists() and not force:
                logger.info("Cached: %s — skipping download.", filepath.name)
                downloaded.append(filepath)
                continue

            logger.info("Downloading %s -> %s", slug, url)
            try:
                resp = client.get(url)
                resp.raise_for_status()

                # Validate we actually got a PDF (check magic bytes or content-type)
                content_type = resp.headers.get("content-type", "")
                if (
                    b"%PDF" not in resp.content[:8]
                    and "pdf" not in content_type.lower()
                ):
                    logger.warning(
                        "Response for %s does not look like a PDF "
                        "(content-type: %s). Saving anyway.",
                        slug,
                        content_type,
                    )

                filepath.write_bytes(resp.content)
                logger.info(
                    "Saved %s (%d bytes).", filepath.name, len(resp.content)
                )
                downloaded.append(filepath)

            except Exception:
                logger.error("Failed to download %s", slug, exc_info=True)

    return downloaded


# ── Convenience: full pipeline step ───────────────────────────────────────


def run_scrape_and_download(force: bool = False) -> List[Path]:
    """Discover links then download all PDFs."""
    links = scrape_pdf_links()
    return download_pdfs(links, force=force)
