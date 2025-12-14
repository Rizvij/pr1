"""Seed data for property management module.

Contains initial data for unit categories.
"""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import UnitCategory

# Unit category seed data with hierarchy rules
UNIT_CATEGORY_SEED_DATA = [
    # Residential categories
    {
        "code": "APARTMENT",
        "name": "Apartment",
        "description": "A self-contained housing unit in a building",
        "is_residential": True,
        "is_commercial": False,
        "allowed_parent_categories": None,  # Root only
        "max_depth": 1,
    },
    {
        "code": "ROOM",
        "name": "Room",
        "description": "A room within an apartment or property",
        "is_residential": True,
        "is_commercial": False,
        "allowed_parent_categories": json.dumps(["APARTMENT"]),
        "max_depth": 2,
    },
    {
        "code": "BED_SPACE",
        "name": "Bed Space",
        "description": "An individual bed space within a room",
        "is_residential": True,
        "is_commercial": False,
        "allowed_parent_categories": json.dumps(["ROOM"]),
        "max_depth": 3,
    },
    # Commercial categories
    {
        "code": "SHOP",
        "name": "Shop",
        "description": "A retail shop unit",
        "is_residential": False,
        "is_commercial": True,
        "allowed_parent_categories": None,  # Root only
        "max_depth": 1,
    },
    {
        "code": "OFFICE",
        "name": "Office",
        "description": "An office space",
        "is_residential": False,
        "is_commercial": True,
        "allowed_parent_categories": None,  # Root only
        "max_depth": 1,
    },
    {
        "code": "WAREHOUSE",
        "name": "Warehouse",
        "description": "A warehouse or storage unit",
        "is_residential": False,
        "is_commercial": True,
        "allowed_parent_categories": None,  # Root only
        "max_depth": 1,
    },
    # Parking categories
    {
        "code": "PARKING",
        "name": "Parking Area",
        "description": "A parking zone or basement parking area",
        "is_residential": False,
        "is_commercial": True,
        "allowed_parent_categories": None,  # Root only
        "max_depth": 1,
    },
    {
        "code": "PARKING_FLOOR",
        "name": "Parking Floor",
        "description": "A floor within a parking structure",
        "is_residential": False,
        "is_commercial": True,
        "allowed_parent_categories": json.dumps(["PARKING"]),
        "max_depth": 2,
    },
    {
        "code": "PARKING_SLOT",
        "name": "Parking Slot",
        "description": "An individual parking space",
        "is_residential": False,
        "is_commercial": True,
        "allowed_parent_categories": json.dumps(["PARKING_FLOOR"]),
        "max_depth": 3,
    },
]


async def seed_unit_categories(db: AsyncSession) -> int:
    """Seed unit categories into the database.

    Args:
        db: AsyncSession database session

    Returns:
        Number of categories created (0 if already seeded)
    """
    # Check if categories already exist
    result = await db.execute(select(UnitCategory).limit(1))
    if result.scalar_one_or_none() is not None:
        return 0  # Already seeded

    created_count = 0
    for category_data in UNIT_CATEGORY_SEED_DATA:
        category = UnitCategory(**category_data, is_active=True)
        db.add(category)
        created_count += 1

    await db.flush()
    return created_count
