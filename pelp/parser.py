"""
PDF table extraction — reads downloaded PELP PDFs and converts the embedded
tables into structured JSON.

Uses **pdfplumber** for text-based table extraction. Each PDF typically
contains a multi-page table with a header row on the first page and
continuation rows on subsequent pages.

Output: one JSON file per category in ``pelp_data/parsed_json/{slug}.json``.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pdfplumber

from .config import PARSED_JSON_DIR, RAW_PDFS_DIR, SLUG_TO_NAME

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────


def _clean_header(raw: str | None) -> str:
    """Normalise a column header string."""
    if raw is None:
        return ""
    # Collapse whitespace / newlines
    text = re.sub(r"\s+", " ", str(raw)).strip()
    return text


def _clean_cell(raw: str | None) -> str:
    """Normalise a table cell value."""
    if raw is None:
        return ""
    return re.sub(r"\s+", " ", str(raw)).strip()


def _is_header_row(row: list[str | None], headers: list[str]) -> bool:
    """
    Heuristic: check whether *row* looks like a repeat of the header row
    (common in multi-page PDFs where the header is repeated on each page).
    """
    cleaned = [_clean_header(c) for c in row]
    if not headers:
        return False
    # Match if at least 60 % of cells are identical to the header.
    matches = sum(1 for a, b in zip(cleaned, headers) if a == b)
    return matches / max(len(headers), 1) >= 0.6


def _looks_like_data_row(row: list[str | None]) -> bool:
    """Return True if the row has enough non-empty cells to be real data."""
    non_empty = sum(1 for c in row if c and str(c).strip())
    return non_empty >= 2


def _extract_brand_model(record: dict[str, Any]) -> Tuple[str, str]:
    """
    Try to locate a brand and model value from the record dict.

    The actual column names vary across PDFs, so we try several common
    patterns.
    """
    brand = ""
    model = ""

    for key, val in record.items():
        kl = key.lower()
        if not val:
            continue
        if "brand" in kl or "manufacturer" in kl or "company" in kl:
            brand = str(val)
        if "model" in kl or "designation" in kl:
            model = str(val)

    return brand, model


# ── Core extraction ───────────────────────────────────────────────────────


def parse_pdf(filepath: Path, category_slug: str) -> List[Dict[str, Any]]:
    """
    Extract tabular data from a single PDF file.

    Returns a list of dicts — one per product row — with keys taken from
    the header row of the table.
    """
    logger.info("Parsing PDF: %s", filepath.name)
    all_rows: List[Dict[str, Any]] = []
    headers: List[str] = []

    try:
        with pdfplumber.open(filepath) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                tables = page.extract_tables()

                if not tables:
                    logger.debug(
                        "Page %d of %s: no tables found.", page_idx + 1, filepath.name
                    )
                    continue

                for table in tables:
                    if not table:
                        continue

                    for row_idx, row in enumerate(table):
                        # First usable row on the very first page -> treat as the header
                        if not headers:
                            headers = [_clean_header(c) for c in row]
                            logger.debug("Detected headers: %s", headers)
                            continue

                        # Skip repeated header rows on subsequent pages
                        if _is_header_row(row, headers):
                            continue

                        if not _looks_like_data_row(row):
                            continue

                        # Build record dict
                        cells = [_clean_cell(c) for c in row]
                        record: Dict[str, Any] = {}
                        for h, c in zip(headers, cells):
                            if h:  # skip unnamed columns
                                record[h] = c

                        # Pad if the row has fewer cells than headers
                        for h in headers[len(cells):]:
                            if h:
                                record[h] = ""

                        record["_category"] = category_slug
                        all_rows.append(record)

    except Exception:
        logger.error("Failed to parse %s", filepath.name, exc_info=True)

    logger.info(
        "Extracted %d product rows from %s.", len(all_rows), filepath.name
    )
    return all_rows


# ── Batch parse + save ────────────────────────────────────────────────────


def parse_all(
    pdf_dir: Path = RAW_PDFS_DIR,
    out_dir: Path = PARSED_JSON_DIR,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse every PDF in *pdf_dir* and save the results as JSON files in
    *out_dir*.

    Returns ``{category_slug: [product_rows …]}``.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    results: Dict[str, List[Dict[str, Any]]] = {}

    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        slug = pdf_path.stem  # filename without extension = category slug
        display_name = SLUG_TO_NAME.get(slug, slug)
        logger.info("Parsing category '%s' (%s) …", display_name, slug)

        rows = parse_pdf(pdf_path, slug)
        results[slug] = rows

        # Write JSON
        json_path = out_dir / f"{slug}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "category": slug,
                    "display_name": display_name,
                    "count": len(rows),
                    "products": rows,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        logger.info("Saved %s (%d records).", json_path.name, len(rows))

    return results


# ── Load cached JSON ──────────────────────────────────────────────────────


def load_parsed_data(
    json_dir: Path = PARSED_JSON_DIR,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Load previously-parsed JSON files and return
    ``{category_slug: [product_rows …]}``.
    """
    data: Dict[str, List[Dict[str, Any]]] = {}

    for json_path in sorted(json_dir.glob("*.json")):
        slug = json_path.stem
        try:
            with open(json_path, encoding="utf-8") as f:
                payload = json.load(f)
            data[slug] = payload.get("products", [])
        except Exception:
            logger.error("Failed to load %s", json_path.name, exc_info=True)

    return data
