"""Property management module for ProRyx.

EP-01: Property & Unit Management
"""

from .models import (
    Property,
    PropertyStatus,
    PropertyUsageType,
    Unit,
    UnitCategory,
    UnitStatus,
)
from .routers import categories_router, router, units_router
from .seed import seed_unit_categories

__all__ = [
    # Models
    "Property",
    "Unit",
    "UnitCategory",
    # Enums
    "PropertyStatus",
    "PropertyUsageType",
    "UnitStatus",
    # Routers
    "router",
    "units_router",
    "categories_router",
    # Seed
    "seed_unit_categories",
]
