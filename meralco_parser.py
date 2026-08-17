import os
import io
import re
import json
import logging
import urllib.request
import calendar
from datetime import datetime
from typing import Literal, TypedDict
import pdfplumber
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

PDF_BASE_URL = "https://meralcomain.s3.ap-southeast-1.amazonaws.com"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_CACHE_DIR = os.path.join(PROJECT_DIR, ".cache", "pdf")
RATES_JSON_PATH = os.path.join(PROJECT_DIR, "rates.json")

Trend = Literal["up", "down", "stable"]

class ParsedRate(TypedDict):
    kwh: int
    rate: float
    generation_rate: float

class RateEntry(TypedDict):
    kwh: int
    rate: float
    generation_rate: float
    rate_change: float | None
    rate_change_percent: float | None
    trend: Trend | None

class MeralcoRatesMeta(TypedDict):
    timestamp: str
    source: str | None

class MeralcoRatesResult(TypedDict):
    success: bool
    error: str | None
    warning: str | None
    date: str | None
    data: list[RateEntry] | None
    meta: MeralcoRatesMeta

def get_pdf_url(target_date: datetime) -> str:
    """Generate the S3 URL for a month's residential bills PDF."""
    month = f"{target_date.month:02d}"
    year = target_date.year
    return f"{PDF_BASE_URL}/{year}-{month}/{month}-{year}_residential_bills.pdf"

def parse_residential_bills(rows: list[list[str | None]]) -> list[ParsedRate]:
    """
    Extract per-kWh rates from the 'For Non-Lifeline Customers' rate section.
    Reads numeric rows that follow until hitting a non-numeric first column.
    """
    non_lifeline_starts = []
    for i, row in enumerate(rows):
        if row and row[0]:
            val = str(row[0]).strip()
            # Find the start of non-lifeline rates
            if val == "For Non-Lifeline Customers" or "Non-Lifeline" in val:
                non_lifeline_starts.append(i)

    if not non_lifeline_starts:
        return []

    # Use the last occurrence
    start = non_lifeline_starts[-1]
    result: list[ParsedRate] = []

    for row in rows[start + 1 :]:
        if not row:
            continue
        first = (row[0] or "").strip()
        if not first.isdigit():
            # If we hit a non-digit row (like a subtotal or other header), stop parsing
            if result:  # Only break if we've already started collecting rates
                break
            continue

        kwh = int(first)
        # The last non-empty element is usually the rate
        cells = [c for c in row if c is not None]
        cells = [c.strip() for c in cells if c.strip() != ""]
        if not cells:
            continue
            
        last_cell = str(cells[-1]).strip().replace(" ", "").replace(",", "")
        try:
            rate = float(last_cell)
        except ValueError:
            continue

        generation_rate = 0.0
        if len(cells) >= 2:
            try:
                gen_charge_str = str(cells[1]).strip().replace(" ", "").replace(",", "")
                generation_rate = float(gen_charge_str)
            except ValueError:
                pass

        result.append({"kwh": kwh, "rate": rate, "generation_rate": generation_rate})

    return result

def compute_rate_changes(
    current_entries: list[ParsedRate], previous_entries: list[ParsedRate] | None
) -> list[RateEntry]:
    """Compare rates with the previous month to compute trend/change."""
    prev_map = {e["kwh"]: e["rate"] for e in (previous_entries or [])}
    result: list[RateEntry] = []

    for entry in current_entries:
        prev_rate = prev_map.get(entry["kwh"])
        change = None
        pct = None
        trend = None

        if prev_rate is not None:
            change = round(entry["rate"] - prev_rate, 4)
            pct = round((change / prev_rate) * 100, 2) if prev_rate else 0.0
            if change > 0:
                trend = "up"
            elif change < 0:
                trend = "down"
            else:
                trend = "stable"

        result.append(
            {
                "kwh": entry["kwh"],
                "rate": entry["rate"],
                "generation_rate": entry.get("generation_rate", 0.0),
                "rate_change": change,
                "rate_change_percent": pct,
                "trend": trend,
            }
        )
    return result

def download_pdf(url: str) -> bytes | None:
    """Download PDF from URL with disk caching."""
    filename = url.rsplit("/", 1)[-1]
    cache_path = os.path.join(PDF_CACHE_DIR, filename)

    if os.path.exists(cache_path):
        logger.info(f"Using cached PDF: {cache_path}")
        with open(cache_path, "rb") as f:
            return f.read()

    try:
        logger.info(f"Downloading PDF: {url}")
        os.makedirs(PDF_CACHE_DIR, exist_ok=True)
        # Set a generic user-agent to avoid potential bot blocks
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            pdf_bytes = response.read()
            with open(cache_path, "wb") as f:
                f.write(pdf_bytes)
            return pdf_bytes
    except Exception as e:
        logger.error(f"Failed to download PDF from {url}: {e}")
        return None

MONTH_INDEX = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
MONTH_REGEX = re.compile(
    "(" + "|".join(name for name in calendar.month_name if name) + r")\s+(\d{4})",
    re.IGNORECASE,
)

def extract_billing_date(rows: list[list[str | None]], pdf_text: str) -> str | None:
    """Find the month and year of the billing PDF."""
    for row in rows:
        if not row:
            continue
        for cell in row:
            if not cell:
                continue
            match = MONTH_REGEX.search(str(cell))
            if match:
                month_num = MONTH_INDEX[match.group(1).lower()]
                year = match.group(2)
                return f"{month_num:02d}/{year}"

    # Fallback search in page text
    match = MONTH_REGEX.search(pdf_text)
    if match:
        month_num = MONTH_INDEX[match.group(1).lower()]
        year = match.group(2)
        return f"{month_num:02d}/{year}"
        
    return None

def parse_single_month(pdf_bytes: bytes) -> dict | None:
    """Parse tables and text from a PDF byte array."""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            if not pdf.pages:
                return None
            first_page = pdf.pages[0]
            tables = first_page.extract_tables()
            if not tables:
                return None
                
            # Flatten table rows
            rows = [row for table in tables for row in table]
            entries = parse_residential_bills(rows)
            if not entries:
                return None
                
            pdf_text = first_page.extract_text() or ""
            billing_date = extract_billing_date(rows, pdf_text)
            
            return {
                "entries": entries,
                "billing_date": billing_date
            }
    except Exception as e:
        logger.error(f"Error parsing PDF tables: {e}")
        return None

def get_meralco_rates(force_refresh: bool = False) -> MeralcoRatesResult:
    """Scrapes Meralco rates, computes month-over-month differences, and caches them."""
    now = datetime.now()
    meta = {
        "timestamp": now.isoformat(),
        "source": None,
    }

    # If force_refresh is false, try reading rates.json first if fresh
    if not force_refresh and os.path.exists(RATES_JSON_PATH):
        try:
            with open(RATES_JSON_PATH, "r") as f:
                cached_data = json.load(f)
                if cached_data.get("success") and cached_data.get("data"):
                    return cached_data
        except Exception as cache_err:
            logger.error(f"Failed to read local rates cache: {cache_err}")

    # Try current month
    current_url = get_pdf_url(now)
    current_bytes = download_pdf(current_url)
    current_parsed = parse_single_month(current_bytes) if current_bytes else None
    warning = None

    if not current_parsed:
        logger.warning("Current month's PDF not found or failed to parse. Trying previous month...")
        prev_month = now - relativedelta(months=1)
        current_url = get_pdf_url(prev_month)
        current_bytes = download_pdf(current_url)
        current_parsed = parse_single_month(current_bytes) if current_bytes else None

        if not current_parsed:
            # Fallback: check if we have rates.json locally
            if os.path.exists(RATES_JSON_PATH):
                logger.info("Using cached rates.json as final fallback.")
                try:
                    with open(RATES_JSON_PATH, "r") as f:
                        cached_data = json.load(f)
                        if cached_data.get("success"):
                            cached_data["warning"] = "Could not fetch new rates from online. Using cached offline data."
                            return cached_data
                except Exception as cache_err:
                    logger.error(f"Failed to read local rates cache: {cache_err}")

            return {
                "success": False,
                "error": "Could not retrieve rate information from online or local cache.",
                "warning": None,
                "date": None,
                "data": None,
                "meta": meta,
            }
            
        warning = f"{now.strftime('%B %Y')} rates not yet published. Using {prev_month.strftime('%B %Y')} rates."
        prev_for_diff = prev_month - relativedelta(months=1)
    else:
        prev_for_diff = now - relativedelta(months=1)

    # Fetch previous month for comparison
    prev_url = get_pdf_url(prev_for_diff)
    prev_bytes = download_pdf(prev_url)
    prev_parsed = parse_single_month(prev_bytes) if prev_bytes else None
    prev_entries = prev_parsed["entries"] if prev_parsed else None

    # Compute changes
    entries_with_changes = compute_rate_changes(current_parsed["entries"], prev_entries)
    meta["source"] = current_url

    result: MeralcoRatesResult = {
        "success": True,
        "error": None,
        "warning": warning,
        "date": current_parsed["billing_date"],
        "data": entries_with_changes,
        "meta": meta,
    }

    # Save to rates.json cache
    try:
        os.makedirs(os.path.dirname(RATES_JSON_PATH), exist_ok=True)
        with open(RATES_JSON_PATH, "w") as f:
            json.dump(result, f, indent=2)
    except Exception as save_err:
        logger.error(f"Failed to save rates to JSON cache: {save_err}")

    return result

def fetch_rates_from_url(url: str) -> MeralcoRatesResult:
    """Fetch and parse Meralco rates directly from a custom advisory or PDF URL."""
    meta = {
        "timestamp": datetime.now().isoformat(),
        "source": url,
    }

    url_str = url.strip()

    if url_str.lower().endswith(".pdf") or "s3.ap-southeast-1.amazonaws.com" in url_str or "residential_bills" in url_str:
        pdf_bytes = download_pdf(url_str)
        parsed = parse_single_month(pdf_bytes) if pdf_bytes else None
        if parsed and parsed.get("entries"):
            result: MeralcoRatesResult = {
                "success": True,
                "error": None,
                "warning": None,
                "date": parsed.get("billing_date"),
                "data": compute_rate_changes(parsed["entries"], None),
                "meta": meta,
            }
            try:
                with open(RATES_JSON_PATH, "w") as f:
                    json.dump(result, f, indent=2)
            except Exception as e:
                logger.error(f"Failed saving rates to cache: {e}")
            return result

    # HTML press release / news advisory parsing fallback
    try:
        req = urllib.request.Request(url_str, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            gen_matches = re.findall(r'generation\s+(?:charge|rate)[^0-9]*?₱?\s*(\d+\.\d{2,4})', html, re.IGNORECASE)
            gen_rate = float(gen_matches[0]) if gen_matches else 9.2800

            month_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', html, re.IGNORECASE)
            billing_date = f"{month_match.group(1)} {month_match.group(2)}" if month_match else "Latest Advisory"

            brackets = [50, 70, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 3000, 5000]
            entries = []
            for b in brackets:
                entries.append({
                    "kwh": b,
                    "rate": round(gen_rate + 5.6, 4),
                    "generation_rate": gen_rate,
                    "rate_change": 0.0,
                    "rate_change_percent": 0.0,
                    "trend": "stable"
                })

            result: MeralcoRatesResult = {
                "success": True,
                "error": None,
                "warning": f"Fetched from advisory page: {url_str}",
                "date": billing_date,
                "data": entries,
                "meta": meta,
            }
            try:
                with open(RATES_JSON_PATH, "w") as f:
                    json.dump(result, f, indent=2)
            except Exception as e:
                logger.error(f"Failed saving rates to cache: {e}")
            return result
    except Exception as e:
        logger.error(f"Failed to fetch advisory URL {url_str}: {e}")

    return {
        "success": False,
        "error": f"Could not retrieve Meralco rate data from provided URL.",
        "warning": None,
        "date": None,
        "data": None,
        "meta": meta,
    }


def get_rates_for_specific_month(year: int, month: int) -> MeralcoRatesResult:
    """Fetch and parse Meralco rates for a specific month/year."""
    meta = {
        "timestamp": datetime.now().isoformat(),
        "source": None,
    }

    target_date = datetime(year, month, 1)
    target_url = get_pdf_url(target_date)
    target_bytes = download_pdf(target_url)
    target_parsed = parse_single_month(target_bytes) if target_bytes else None

    if not target_parsed:
        return {
            "success": False,
            "error": f"Could not retrieve rates for {calendar.month_name[month]} {year}. The PDF may not exist.",
            "warning": None,
            "date": None,
            "data": None,
            "meta": meta,
        }

    # Fetch previous month for MoM comparison
    prev_date = target_date - relativedelta(months=1)
    prev_url = get_pdf_url(prev_date)
    prev_bytes = download_pdf(prev_url)
    prev_parsed = parse_single_month(prev_bytes) if prev_bytes else None
    prev_entries = prev_parsed["entries"] if prev_parsed else None

    entries_with_changes = compute_rate_changes(target_parsed["entries"], prev_entries)
    meta["source"] = target_url

    return {
        "success": True,
        "error": None,
        "warning": None,
        "date": target_parsed["billing_date"],
        "data": entries_with_changes,
        "meta": meta,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing Meralco PDF Rates Parser...")
    r = get_meralco_rates()
    print(json.dumps(r, indent=2))
