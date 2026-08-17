"""
Pydantic models for PELP API request / response schemas.
"""

from __future__ import annotations

from typing import Any, Optional, Dict, List, Union

try:
    from pydantic import BaseModel, Field
except ImportError:
    # Graceful fallback dummy if pydantic is not installed yet
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def dict(self):
            return self.__dict__

    def Field(default=None, default_factory=None, description=None, **kwargs):
        if default_factory is not None:
            return default_factory()
        return default


# ---------------------------------------------------------------------------
# Product record
# ---------------------------------------------------------------------------
class ApplianceProduct(BaseModel):
    """
    A single appliance product extracted from a PELP PDF.

    Because the column headers vary across the 6 appliance categories, we
    store every row as a flat dict of string key-value pairs, plus some
    commonly shared fields promoted to first-class attributes.
    """

    category: str = Field(..., description="Appliance category slug")
    brand: str = Field("", description="Brand / manufacturer name")
    model: str = Field("", description="Model designation")
    raw_fields: dict[str, Any] = Field(
        default_factory=dict,
        description="All columns extracted from the PDF row",
    )


# ---------------------------------------------------------------------------
# API responses
# ---------------------------------------------------------------------------
class CategorySummary(BaseModel):
    """Summary info for a single category."""

    category: str
    display_name: str
    count: int


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = "ok"
    service: str = "DOE PELP Appliance Data API"
    categories_available: list[CategorySummary] = []
    total_products: int = 0


class CategoryResponse(BaseModel):
    """Category products response."""

    category: str
    display_name: str
    count: int
    products: list[ApplianceProduct]


class AllAppliancesResponse(BaseModel):
    """All categories response."""

    total_count: int
    categories: list[CategoryResponse]


class ScrapeResult(BaseModel):
    """Pipeline trigger response."""

    status: str
    message: str
    pdfs_downloaded: int = 0
    categories_parsed: int = 0
    total_products_extracted: int = 0
    details: dict[str, int] = Field(
        default_factory=dict,
        description="Product count per category slug",
    )


class SearchResponse(BaseModel):
    """Search response model."""

    query: dict[str, Optional[str]]
    total_results: int
    results: list[ApplianceProduct]
