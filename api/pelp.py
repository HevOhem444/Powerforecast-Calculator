import os
import json
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from typing import Dict, List, Any, Optional

logger = logging.getLogger("pelp_api")

CATEGORIES = {
    "Air Conditioners": "air-conditioners",
    "Lighting Products": "lighting-products",
    "Refrigerating Appliances": "refrigerating-appliances",
    "Television Sets": "television-sets",
    "Electric Fans": "electric-fans",
    "Clothes Washing Machines": "clothes-washing-machines",
}

SLUG_TO_NAME = {v: k for k, v in CATEGORIES.items()}

# Cache for loaded JSON data
_PELP_DATA_CACHE: Optional[Dict[str, List[Dict[str, Any]]]] = None


def find_pelp_json_dir() -> str:
    """Locate the parsed_json directory in the workspace or Vercel lambda runtime."""
    file_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(file_dir)
    cwd = os.getcwd()
    candidates = [
        os.path.join(base_dir, "pelp_data", "parsed_json"),
        os.path.join(cwd, "pelp_data", "parsed_json"),
        os.path.join(file_dir, "pelp_data", "parsed_json"),
        os.path.join(file_dir, "..", "pelp_data", "parsed_json"),
        os.path.join("/var/task", "pelp_data", "parsed_json"),
        os.path.join(base_dir, "data", "parsed_json"),
        os.path.join(base_dir, "Appliances_PELP", "data", "parsed_json"),
        os.path.join(base_dir, "..", "Appliances_PELP", "data", "parsed_json"),
    ]
    for p in candidates:
        norm_p = os.path.normpath(p)
        if os.path.exists(norm_p) and os.path.isdir(norm_p):
            return norm_p
    # Default fallback
    return os.path.normpath(candidates[0])


def load_pelp_data(force_reload: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    """Load and cache all parsed PELP appliance datasets."""
    global _PELP_DATA_CACHE
    if _PELP_DATA_CACHE is not None and not force_reload:
        return _PELP_DATA_CACHE

    json_dir = find_pelp_json_dir()
    data: Dict[str, List[Dict[str, Any]]] = {}

    for slug in CATEGORIES.values():
        file_path = os.path.join(json_dir, f"{slug}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                    data[slug] = payload.get("products", [])
            except Exception as e:
                logger.error("Failed to load %s: %s", file_path, e)
                data[slug] = []
        else:
            data[slug] = []

    _PELP_DATA_CACHE = data
    return data


def extract_normalized_product(row: Dict[str, Any], category_slug: str) -> Dict[str, Any]:
    """Extract standard properties from raw PELP row dictionary."""
    brand = ""
    model = ""
    power_watts = 0.0
    monthly_kwh = 0.0
    energy_rating_type = ""
    energy_rating_value = ""
    star_rating = ""
    control_no = ""
    product_name = ""
    doe_link = ""

    for k, v in row.items():
        kl = k.lower()
        val_str = str(v).strip() if v is not None else ""

        if ("brand" in kl or "manufacturer" in kl) and not brand and val_str:
            brand = val_str
        elif ("model" in kl or "designation" in kl) and not model and val_str:
            model = val_str
        elif ("product name" in kl) and not product_name and val_str:
            product_name = val_str
        elif ("control no" in kl) and not control_no and val_str:
            control_no = val_str
        elif ("public product link" in kl) and not doe_link and val_str:
            doe_link = val_str

        # Wattage detection
        if ("power rating" in kl or "rated power" in kl or "power (watts)" in kl) and val_str:
            try:
                # Clean non-digit characters except period
                clean_num = "".join(c for c in val_str if c.isdigit() or c == ".")
                if clean_num:
                    power_watts = float(clean_num)
            except Exception:
                pass

        # Monthly kWh detection
        if ("monthly" in kl and "kwh" in kl) or ("monthly" in kl and "consumption" in kl):
            try:
                clean_num = "".join(c for c in val_str if c.isdigit() or c == ".")
                if clean_num:
                    monthly_kwh = float(clean_num)
            except Exception:
                pass

        # Energy Efficiency Rating
        if "energy efficiency rating" in kl or "energy efficiency factor" in kl or "cspf" in kl or "eef" in kl or "eer" in kl:
            if not energy_rating_value and val_str:
                energy_rating_value = val_str
                if "cspf" in kl:
                    energy_rating_type = "CSPF"
                elif "eef" in kl:
                    energy_rating_type = "EEF"
                elif "eer" in kl:
                    energy_rating_type = "EER"
                else:
                    energy_rating_type = "EER"

        if "performance rating" in kl or "star" in kl:
            if not star_rating and val_str:
                star_rating = val_str

    # Fallback wattage estimate if missing in PDF table but monthly_kwh is present
    if power_watts <= 0 and monthly_kwh > 0:
        power_watts = round((monthly_kwh / 30.0 / 8.0) * 1000.0, 1)

    return {
        "category": category_slug,
        "category_name": SLUG_TO_NAME.get(category_slug, category_slug),
        "brand": brand or row.get("COMPANY", "Unknown Brand"),
        "model": model or row.get("MODEL NO./CODE", ""),
        "product_name": product_name or row.get("PRODUCT NAME", ""),
        "control_no": control_no,
        "power_watts": power_watts,
        "monthly_kwh": monthly_kwh,
        "energy_rating_type": energy_rating_type,
        "energy_rating_value": energy_rating_value,
        "star_rating": star_rating,
        "doe_link": doe_link,
        "raw_fields": {k: v for k, v in row.items() if not k.startswith("_")},
    }


def get_pelp_health() -> Dict[str, Any]:
    """Overview of loaded PELP datasets and category counts."""
    data = load_pelp_data()
    summaries = []
    total = 0
    for slug in CATEGORIES.values():
        products = data.get(slug, [])
        count = len(products)
        total += count
        summaries.append({
            "category": slug,
            "display_name": SLUG_TO_NAME.get(slug, slug),
            "count": count
        })
    return {
        "status": "ok",
        "service": "DOE PELP Appliance Data API",
        "categories_available": summaries,
        "total_products": total
    }


def get_pelp_categories() -> List[Dict[str, Any]]:
    """List all categories with metadata."""
    data = load_pelp_data()
    return [
        {
            "category": slug,
            "display_name": SLUG_TO_NAME.get(slug, slug),
            "count": len(data.get(slug, []))
        }
        for slug in CATEGORIES.values()
    ]


def get_pelp_category_products(category_slug: str, limit: int = 100) -> Dict[str, Any]:
    """Fetch products for a single category."""
    if category_slug not in SLUG_TO_NAME:
        return {"error": f"Unknown category '{category_slug}'", "products": []}

    data = load_pelp_data()
    rows = data.get(category_slug, [])
    products = [extract_normalized_product(r, category_slug) for r in rows[:limit]]

    return {
        "category": category_slug,
        "display_name": SLUG_TO_NAME[category_slug],
        "total_count": len(rows),
        "limit": limit,
        "products": products
    }


def search_pelp_appliances(
    query_str: Optional[str] = None,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Search and filter appliances across all PELP datasets."""
    data = load_pelp_data()
    results = []

    clean_query = (query_str or "").strip().lower()
    query_tokens = clean_query.split() if clean_query else []

    slugs = [category] if category and category in SLUG_TO_NAME else list(CATEGORIES.values())

    for slug in slugs:
        display_name = SLUG_TO_NAME.get(slug, slug).lower()
        rows = data.get(slug, [])

        for row in rows:
            product = extract_normalized_product(row, slug)

            # Specific brand / model filters
            if brand and brand.lower() not in product["brand"].lower():
                continue
            if model and model.lower() not in product["model"].lower():
                continue

            # Multi-token general search
            if query_tokens:
                searchable_parts = [
                    product["brand"].lower(),
                    product["model"].lower(),
                    product["product_name"].lower(),
                    product["category"].lower(),
                    display_name,
                    product.get("control_no", "").lower(),
                ]
                for v in product["raw_fields"].values():
                    if v:
                        searchable_parts.append(str(v).lower())

                full_text = " ".join(searchable_parts)
                if not all(token in full_text for token in query_tokens):
                    continue

            results.append(product)
            if limit and len(results) >= limit:
                break
        if limit and len(results) >= limit:
            break

    return {
        "success": True,
        "query": {
            "search_query": query_str,
            "brand": brand,
            "model": model,
            "category": category,
        },
        "total_results": len(results),
        "results": results,
    }


class handler(BaseHTTPRequestHandler):
    def _send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors()
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._send_cors()
        self.end_headers()

        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        params = parse_qs(parsed.query)

        try:
            is_search = (
                path in ['/api/pelp/search', '/api/pelp/appliances/search', '/search']
                or path.endswith('/search')
                or 'q' in params
                or 'search_query' in params
                or 'brand' in params
                or 'model' in params
            )
            is_categories = (
                path in ['/api/pelp/categories', '/categories']
                or path.endswith('/categories')
            )
            is_category_slug = (
                '/category/' in path or '/appliances/' in path
            )

            if is_search:
                q = params.get('q', params.get('search_query', [None]))[0]
                brand = params.get('brand', [None])[0]
                model = params.get('model', [None])[0]
                category = params.get('category', [None])[0]
                try:
                    limit = int(params.get('limit', [50])[0])
                except ValueError:
                    limit = 50
                res = search_pelp_appliances(
                    query_str=q,
                    brand=brand,
                    model=model,
                    category=category,
                    limit=limit
                )
            elif is_categories:
                res = {"categories": get_pelp_categories()}
            elif is_category_slug:
                parts = path.split('/')
                slug = parts[-1]
                try:
                    limit = int(params.get('limit', [100])[0])
                except ValueError:
                    limit = 100
                res = get_pelp_category_products(slug, limit=limit)
            else:
                res = get_pelp_health()

            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            err_res = {"error": "Internal PELP API Error", "message": str(e)}
            self.wfile.write(json.dumps(err_res).encode('utf-8'))

