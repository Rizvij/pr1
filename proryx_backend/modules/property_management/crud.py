"""CRUD operations for property management module."""

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Property, PropertyStatus, Unit, UnitCategory, UnitStatus

# ----- Unit Category CRUD -----


async def get_unit_category_by_id(
    db: AsyncSession, category_id: int
) -> UnitCategory | None:
    """Get a unit category by ID."""
    result = await db.execute(
        select(UnitCategory).where(UnitCategory.id == category_id)
    )
    return result.scalar_one_or_none()


async def get_unit_category_by_code(db: AsyncSession, code: str) -> UnitCategory | None:
    """Get a unit category by code."""
    result = await db.execute(select(UnitCategory).where(UnitCategory.code == code))
    return result.scalar_one_or_none()


async def get_all_unit_categories(
    db: AsyncSession, is_active: bool | None = None
) -> list[UnitCategory]:
    """Get all unit categories."""
    query = select(UnitCategory)
    if is_active is not None:
        query = query.where(UnitCategory.is_active == is_active)
    result = await db.execute(query.order_by(UnitCategory.name))
    return list(result.scalars().all())


async def create_unit_category(
    db: AsyncSession,
    code: str,
    name: str,
    description: str | None = None,
) -> UnitCategory:
    """Create a new unit category."""
    category = UnitCategory(
        code=code.upper(),
        name=name,
        description=description,
        is_active=True,
    )
    db.add(category)
    await db.flush()
    return category


# ----- Property CRUD -----


async def get_property_by_id(
    db: AsyncSession,
    property_id: int,
    account_id: int,
    company_id: int,
    include_units: bool = False,
    include_deleted: bool = False,
) -> Property | None:
    """Get a property by ID within tenant scope."""
    filters = [
        Property.id == property_id,
        Property.account_id == account_id,
        Property.company_id == company_id,
    ]
    if not include_deleted:
        filters.append(Property.is_deleted == False)  # noqa: E712
    query = select(Property).where(and_(*filters))
    if include_units:
        query = query.options(selectinload(Property.units).selectinload(Unit.category))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_property_by_code(
    db: AsyncSession,
    property_code: str,
    account_id: int,
    company_id: int,
) -> Property | None:
    """Get a property by code within tenant scope."""
    result = await db.execute(
        select(Property).where(
            and_(
                Property.property_code == property_code,
                Property.account_id == account_id,
                Property.company_id == company_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_properties(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    skip: int = 0,
    limit: int = 100,
    status: PropertyStatus | None = None,
    usage_type: str | None = None,
    search: str | None = None,
    include_deleted: bool = False,
) -> tuple[list[Property], int]:
    """Get properties with filtering and pagination.

    Returns:
        Tuple of (list of properties, total count)
    """
    # Base query
    base_filters = [
        Property.account_id == account_id,
        Property.company_id == company_id,
    ]
    if not include_deleted:
        base_filters.append(Property.is_deleted == False)  # noqa: E712

    # Build filter conditions
    filters = list(base_filters)
    if status:
        filters.append(Property.status == status)
    if usage_type:
        filters.append(Property.usage_type == usage_type)
    if search:
        search_filter = f"%{search}%"
        filters.append(
            (Property.property_name.ilike(search_filter))
            | (Property.property_code.ilike(search_filter))
            | (Property.address_line_1.ilike(search_filter))
        )

    # Count query
    count_query = select(func.count(Property.id)).where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Data query
    data_query = (
        select(Property)
        .where(and_(*filters))
        .order_by(Property.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(data_query)
    properties = list(result.scalars().all())

    return properties, total


async def create_property(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    property_code: str,
    property_name: str,
    usage_type: str,
    latitude: float,
    longitude: float,
    status: PropertyStatus = PropertyStatus.ACTIVE,
    **kwargs,
) -> Property:
    """Create a new property."""
    import uuid

    # Get next ID for this tenant
    result = await db.execute(
        select(Property.id)
        .where(
            and_(Property.account_id == account_id, Property.company_id == company_id)
        )
        .order_by(Property.id.desc())
        .limit(1)
    )
    max_id = result.scalar_one_or_none()
    next_id = (max_id or 0) + 1

    property_obj = Property(
        account_id=account_id,
        company_id=company_id,
        id=next_id,
        uuid=str(uuid.uuid4()),
        property_code=property_code,
        property_name=property_name,
        usage_type=usage_type,
        latitude=latitude,
        longitude=longitude,
        status=status,
        is_deleted=False,
        **kwargs,
    )
    db.add(property_obj)
    await db.flush()
    return property_obj


async def update_property(
    db: AsyncSession,
    property_obj: Property,
    **kwargs,
) -> Property:
    """Update a property."""
    for key, value in kwargs.items():
        if value is not None and hasattr(property_obj, key):
            setattr(property_obj, key, value)
    await db.flush()
    return property_obj


async def soft_delete_property(db: AsyncSession, property_obj: Property) -> Property:
    """Soft-delete a property by setting is_deleted=True."""
    property_obj.is_deleted = True
    await db.flush()
    return property_obj


async def hard_delete_property(db: AsyncSession, property_obj: Property) -> None:
    """Permanently delete a property (will cascade to units). Use with caution."""
    await db.delete(property_obj)
    await db.flush()


async def get_active_units_count(
    db: AsyncSession,
    property_id: int,
    account_id: int,
    company_id: int,
) -> int:
    """Get count of active (non-INACTIVE) units for a property.

    Used for delete validation - cannot delete property with active units.
    """
    result = await db.execute(
        select(func.count(Unit.id)).where(
            and_(
                Unit.account_id == account_id,
                Unit.company_id == company_id,
                Unit.property_id == property_id,
                Unit.status != UnitStatus.INACTIVE,
            )
        )
    )
    return result.scalar_one()


# ----- Unit CRUD -----


async def get_unit_by_id(
    db: AsyncSession,
    unit_id: int,
    account_id: int,
    company_id: int,
    include_children: bool = False,
) -> Unit | None:
    """Get a unit by ID within tenant scope."""
    query = (
        select(Unit)
        .options(selectinload(Unit.category))
        .where(
            and_(
                Unit.id == unit_id,
                Unit.account_id == account_id,
                Unit.company_id == company_id,
            )
        )
    )
    # Note: Unit.children relationship removed due to composite key complexity
    # Child units should be fetched via get_child_units() in services.py if needed
    if include_children:
        pass  # Children fetched separately via application-level queries
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_unit_by_code(
    db: AsyncSession,
    unit_code: str,
    property_id: int,
    account_id: int,
    company_id: int,
) -> Unit | None:
    """Get a unit by code within property and tenant scope."""
    result = await db.execute(
        select(Unit)
        .options(selectinload(Unit.category))
        .where(
            and_(
                Unit.unit_code == unit_code,
                Unit.property_id == property_id,
                Unit.account_id == account_id,
                Unit.company_id == company_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_units_by_property(
    db: AsyncSession,
    property_id: int,
    account_id: int,
    company_id: int,
    skip: int = 0,
    limit: int = 100,
    status: UnitStatus | None = None,
    is_leaf: bool | None = None,
    parent_unit_id: int | None = None,
) -> tuple[list[Unit], int]:
    """Get units for a property with filtering.

    Returns:
        Tuple of (list of units, total count)
    """
    # Base filter
    base_filter = and_(
        Unit.account_id == account_id,
        Unit.company_id == company_id,
        Unit.property_id == property_id,
    )

    filters = [base_filter]
    if status:
        filters.append(Unit.status == status)
    if is_leaf is not None:
        filters.append(Unit.is_leaf == is_leaf)
    if parent_unit_id is not None:
        filters.append(Unit.parent_unit_id == parent_unit_id)

    # Count query
    count_query = select(func.count(Unit.id)).where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Data query
    data_query = (
        select(Unit)
        .options(selectinload(Unit.category))
        .where(and_(*filters))
        .order_by(Unit.unit_code)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(data_query)
    units = list(result.scalars().all())

    return units, total


async def get_root_units(
    db: AsyncSession,
    property_id: int,
    account_id: int,
    company_id: int,
) -> list[Unit]:
    """Get root units (no parent) for a property."""
    result = await db.execute(
        select(Unit)
        .options(selectinload(Unit.category))
        .where(
            and_(
                Unit.account_id == account_id,
                Unit.company_id == company_id,
                Unit.property_id == property_id,
                Unit.parent_unit_id.is_(None),
            )
        )
        .order_by(Unit.unit_code)
    )
    return list(result.scalars().all())


async def create_unit(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    property_id: int,
    unit_code: str,
    category_id: int,
    name: str | None = None,
    parent_unit_id: int | None = None,
    is_leaf: bool = True,
    status: UnitStatus = UnitStatus.AVAILABLE,
    **kwargs,
) -> Unit:
    """Create a new unit."""
    import uuid

    # Get next ID for this tenant
    result = await db.execute(
        select(Unit.id)
        .where(and_(Unit.account_id == account_id, Unit.company_id == company_id))
        .order_by(Unit.id.desc())
        .limit(1)
    )
    max_id = result.scalar_one_or_none()
    next_id = (max_id or 0) + 1

    unit = Unit(
        account_id=account_id,
        company_id=company_id,
        id=next_id,
        uuid=str(uuid.uuid4()),
        property_id=property_id,
        unit_code=unit_code,
        display_name=name,
        category_id=category_id,
        parent_unit_id=parent_unit_id,
        is_leaf=is_leaf,
        status=status,
        **kwargs,
    )
    db.add(unit)
    await db.flush()
    return unit


async def update_unit(
    db: AsyncSession,
    unit: Unit,
    **kwargs,
) -> Unit:
    """Update a unit."""
    for key, value in kwargs.items():
        if value is not None and hasattr(unit, key):
            setattr(unit, key, value)
    await db.flush()
    return unit


async def delete_unit(db: AsyncSession, unit: Unit) -> None:
    """Delete a unit."""
    await db.delete(unit)
    await db.flush()


async def get_unit_children_count(
    db: AsyncSession,
    unit_id: int,
    account_id: int,
    company_id: int,
) -> int:
    """Get count of child units for a unit."""
    result = await db.execute(
        select(func.count(Unit.id)).where(
            and_(
                Unit.account_id == account_id,
                Unit.company_id == company_id,
                Unit.parent_unit_id == unit_id,
            )
        )
    )
    return result.scalar_one()


async def get_leaf_units(
    db: AsyncSession,
    property_id: int,
    account_id: int,
    company_id: int,
    status: UnitStatus | None = None,
    category_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Unit], int]:
    """Get all leaf units (rentable) for a property.

    Args:
        db: Database session
        property_id: Property ID
        account_id: Account ID
        company_id: Company ID
        status: Optional status filter
        category_id: Optional category filter
        skip: Pagination offset
        limit: Pagination limit

    Returns:
        Tuple of (list of leaf units, total count)
    """
    # Base filter: leaf units only
    filters = [
        Unit.account_id == account_id,
        Unit.company_id == company_id,
        Unit.property_id == property_id,
        Unit.is_leaf == True,  # noqa: E712
    ]

    if status:
        filters.append(Unit.status == status)
    if category_id:
        filters.append(Unit.category_id == category_id)

    # Count query
    count_query = select(func.count(Unit.id)).where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Data query
    data_query = (
        select(Unit)
        .options(selectinload(Unit.category))
        .where(and_(*filters))
        .order_by(Unit.unit_code)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(data_query)
    units = list(result.scalars().all())

    return units, total


async def get_leasable_units(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    property_id: int | None = None,
    category_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Unit], int]:
    """Get all leasable units (leaf + available) for the leasing screen.

    This is the main query for the leasing screen dropdown/selection.

    Args:
        db: Database session
        account_id: Account ID
        company_id: Company ID
        property_id: Optional property filter
        category_id: Optional category filter
        skip: Pagination offset
        limit: Pagination limit

    Returns:
        Tuple of (list of leasable units, total count)
    """
    # Base filter: leaf units that are available
    filters = [
        Unit.account_id == account_id,
        Unit.company_id == company_id,
        Unit.is_leaf == True,  # noqa: E712
        Unit.status == UnitStatus.AVAILABLE,
    ]

    if property_id:
        filters.append(Unit.property_id == property_id)
    if category_id:
        filters.append(Unit.category_id == category_id)

    # Count query
    count_query = select(func.count(Unit.id)).where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Data query with property info
    data_query = (
        select(Unit)
        .options(selectinload(Unit.category), selectinload(Unit.property))
        .where(and_(*filters))
        .order_by(Unit.property_id, Unit.unit_code)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(data_query)
    units = list(result.scalars().all())

    return units, total
