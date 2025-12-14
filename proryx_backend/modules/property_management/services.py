"""Property management business logic services."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions import NotFoundError, ValidationError
from . import crud
from .models import Property, Unit, UnitCategory
from .schemas import (
    PropertyCreate,
    PropertyUpdate,
    UnitCreate,
    UnitHierarchyResponse,
    UnitUpdate,
)

# Maximum allowed hierarchy depth for units
MAX_UNIT_DEPTH = 3


async def _get_unit_depth(
    db: AsyncSession,
    unit_id: int | None,
    account_id: int,
    company_id: int,
) -> int:
    """Calculate the depth of a unit by traversing up the parent chain.

    Args:
        db: Database session
        unit_id: The unit ID to calculate depth for (None = root level)
        account_id: Account ID
        company_id: Company ID

    Returns:
        Depth level (1 for root units, 2 for first-level children, etc.)
    """
    if unit_id is None:
        return 0  # No parent means this will be at depth 1

    depth = 0
    current_id = unit_id

    while current_id is not None:
        depth += 1
        unit = await crud.get_unit_by_id(db, current_id, account_id, company_id)
        if unit is None:
            break
        current_id = unit.parent_unit_id

        # Safety check to prevent infinite loops
        if depth > MAX_UNIT_DEPTH + 1:
            break

    return depth


def _validate_category_parent(
    category: UnitCategory,
    parent_category: UnitCategory | None,
) -> None:
    """Validate that the parent category is allowed for this category.

    Args:
        category: The category of the new unit
        parent_category: The category of the parent unit (None if root)

    Raises:
        ValidationError: If parent category is not allowed
    """
    if not category.allowed_parent_categories:
        # No restriction means this category can only be a root
        if parent_category is not None:
            raise ValidationError(
                f"Category '{category.code}' can only be used for root units (no parent)"
            )
        return

    # Parse allowed parent categories
    try:
        allowed = json.loads(category.allowed_parent_categories)
    except (json.JSONDecodeError, TypeError):
        allowed = []

    if parent_category is None:
        raise ValidationError(
            f"Category '{category.code}' requires a parent unit of category: {allowed}"
        )

    if parent_category.code not in allowed:
        raise ValidationError(
            f"Category '{category.code}' cannot have parent of category "
            f"'{parent_category.code}'. Allowed: {allowed}"
        )


async def create_property(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    data: PropertyCreate,
) -> Property:
    """Create a new property with validation.

    Args:
        db: Database session
        account_id: Account ID
        company_id: Company ID
        data: Property creation data

    Returns:
        Created property

    Raises:
        ValidationError: If property code already exists
    """
    # Check for duplicate property code
    existing = await crud.get_property_by_code(
        db, data.property_code, account_id, company_id
    )
    if existing:
        raise ValidationError(
            f"Property with code '{data.property_code}' already exists"
        )

    property_obj = await crud.create_property(
        db=db,
        account_id=account_id,
        company_id=company_id,
        property_code=data.property_code,
        property_name=data.property_name,
        usage_type=data.usage_type,
        latitude=data.latitude,
        longitude=data.longitude,
        status=data.status,
        address_line_1=data.address_line_1,
        address_line_2=data.address_line_2,
        city=data.city,
        state=data.state,
        country=data.country,
        postal_code=data.postal_code,
        total_floors=data.total_floors,
        year_built=data.year_built,
        notes=data.notes,
    )

    await db.commit()
    return property_obj


async def update_property(
    db: AsyncSession,
    property_id: int,
    account_id: int,
    company_id: int,
    data: PropertyUpdate,
) -> Property:
    """Update a property.

    Args:
        db: Database session
        property_id: Property ID to update
        account_id: Account ID
        company_id: Company ID
        data: Update data

    Returns:
        Updated property

    Raises:
        NotFoundError: If property not found
        ValidationError: If new property code conflicts
    """
    property_obj = await crud.get_property_by_id(
        db, property_id, account_id, company_id
    )
    if not property_obj:
        raise NotFoundError(f"Property with ID {property_id} not found")

    # Check for duplicate code if changing
    if data.property_code and data.property_code != property_obj.property_code:
        existing = await crud.get_property_by_code(
            db, data.property_code, account_id, company_id
        )
        if existing:
            raise ValidationError(
                f"Property with code '{data.property_code}' already exists"
            )

    updated = await crud.update_property(
        db,
        property_obj,
        **data.model_dump(exclude_unset=True),
    )

    await db.commit()
    return updated


async def delete_property(
    db: AsyncSession,
    property_id: int,
    account_id: int,
    company_id: int,
) -> None:
    """Soft-delete a property.

    Args:
        db: Database session
        property_id: Property ID to delete
        account_id: Account ID
        company_id: Company ID

    Raises:
        NotFoundError: If property not found
        ValidationError: If property has active units
    """
    property_obj = await crud.get_property_by_id(
        db, property_id, account_id, company_id
    )
    if not property_obj:
        raise NotFoundError(f"Property with ID {property_id} not found")

    # Check for active units
    active_units_count = await crud.get_active_units_count(
        db, property_id, account_id, company_id
    )
    if active_units_count > 0:
        raise ValidationError(
            f"Cannot delete property with {active_units_count} active unit(s). "
            "Deactivate all units first."
        )

    await crud.soft_delete_property(db, property_obj)
    await db.commit()


async def create_unit(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    data: UnitCreate,
) -> Unit:
    """Create a new unit with validation.

    Args:
        db: Database session
        account_id: Account ID
        company_id: Company ID
        data: Unit creation data

    Returns:
        Created unit

    Raises:
        ValidationError: If validation fails (depth, category, duplicate code)
        NotFoundError: If property, category, or parent unit not found
    """
    # Verify property exists
    property_obj = await crud.get_property_by_id(
        db, data.property_id, account_id, company_id
    )
    if not property_obj:
        raise NotFoundError(f"Property with ID {data.property_id} not found")

    # Verify category exists
    category = await crud.get_unit_category_by_id(db, data.category_id)
    if not category:
        raise NotFoundError(f"Unit category with ID {data.category_id} not found")

    # Validate parent unit and hierarchy constraints
    parent = None
    parent_category = None

    if data.parent_unit_id:
        parent = await crud.get_unit_by_id(
            db, data.parent_unit_id, account_id, company_id
        )
        if not parent:
            raise NotFoundError(f"Parent unit with ID {data.parent_unit_id} not found")
        if parent.property_id != data.property_id:
            raise ValidationError("Parent unit must be in the same property")

        # Get parent's category for validation
        parent_category = await crud.get_unit_category_by_id(db, parent.category_id)

    # Validate category parent constraints
    _validate_category_parent(category, parent_category)

    # Validate max depth constraint
    parent_depth = await _get_unit_depth(
        db, data.parent_unit_id, account_id, company_id
    )
    new_depth = parent_depth + 1

    if new_depth > MAX_UNIT_DEPTH:
        raise ValidationError(
            f"Maximum unit hierarchy depth is {MAX_UNIT_DEPTH}. "
            f"Cannot create unit at depth {new_depth}."
        )

    # Update parent's is_leaf to False since it now has children
    if parent and parent.is_leaf:
        await crud.update_unit(db, parent, is_leaf=False)

    # Check for duplicate unit code within property
    existing = await crud.get_unit_by_code(
        db, data.unit_code, data.property_id, account_id, company_id
    )
    if existing:
        raise ValidationError(
            f"Unit with code '{data.unit_code}' already exists in this property"
        )

    unit = await crud.create_unit(
        db=db,
        account_id=account_id,
        company_id=company_id,
        property_id=data.property_id,
        unit_code=data.unit_code,
        name=data.display_name,
        category_id=data.category_id,
        parent_unit_id=data.parent_unit_id,
        is_leaf=data.is_leaf,
        status=data.status,
        floor_number=data.floor_number,
        area_sqm=data.area_sqm,
        capacity=data.capacity,
        notes=data.notes,
    )

    await db.commit()
    return unit


async def update_unit(
    db: AsyncSession,
    unit_id: int,
    account_id: int,
    company_id: int,
    data: UnitUpdate,
) -> Unit:
    """Update a unit.

    Args:
        db: Database session
        unit_id: Unit ID to update
        account_id: Account ID
        company_id: Company ID
        data: Update data

    Returns:
        Updated unit

    Raises:
        NotFoundError: If unit not found
        ValidationError: If validation fails
    """
    unit = await crud.get_unit_by_id(db, unit_id, account_id, company_id)
    if not unit:
        raise NotFoundError(f"Unit with ID {unit_id} not found")

    # Check for duplicate code if changing
    if data.unit_code and data.unit_code != unit.unit_code:
        existing = await crud.get_unit_by_code(
            db, data.unit_code, unit.property_id, account_id, company_id
        )
        if existing:
            raise ValidationError(
                f"Unit with code '{data.unit_code}' already exists in this property"
            )

    # Validate category if changing
    if data.category_id:
        category = await crud.get_unit_category_by_id(db, data.category_id)
        if not category:
            raise NotFoundError(f"Unit category with ID {data.category_id} not found")

    # Validate parent if changing
    if data.parent_unit_id is not None:
        if data.parent_unit_id == unit_id:
            raise ValidationError("Unit cannot be its own parent")

        if data.parent_unit_id:
            parent = await crud.get_unit_by_id(
                db, data.parent_unit_id, account_id, company_id
            )
            if not parent:
                raise NotFoundError(
                    f"Parent unit with ID {data.parent_unit_id} not found"
                )
            if parent.property_id != unit.property_id:
                raise ValidationError("Parent unit must be in the same property")

    updated = await crud.update_unit(
        db,
        unit,
        **data.model_dump(exclude_unset=True),
    )

    # Recompute is_leaf for old and new parent
    await _recompute_is_leaf(db, account_id, company_id, unit)

    await db.commit()
    return updated


async def delete_unit(
    db: AsyncSession,
    unit_id: int,
    account_id: int,
    company_id: int,
) -> None:
    """Delete a unit.

    Args:
        db: Database session
        unit_id: Unit ID to delete
        account_id: Account ID
        company_id: Company ID

    Raises:
        NotFoundError: If unit not found
        ValidationError: If unit has children
    """
    unit = await crud.get_unit_by_id(db, unit_id, account_id, company_id)
    if not unit:
        raise NotFoundError(f"Unit with ID {unit_id} not found")

    # Check if unit has children
    children_count = await crud.get_unit_children_count(
        db, unit_id, account_id, company_id
    )
    if children_count > 0:
        raise ValidationError(
            f"Cannot delete unit with {children_count} child unit(s). "
            "Delete children first."
        )

    parent_id = unit.parent_unit_id
    await crud.delete_unit(db, unit)

    # Recompute is_leaf for parent if exists
    if parent_id:
        parent = await crud.get_unit_by_id(db, parent_id, account_id, company_id)
        if parent:
            children_count = await crud.get_unit_children_count(
                db, parent_id, account_id, company_id
            )
            if children_count == 0 and not parent.is_leaf:
                await crud.update_unit(db, parent, is_leaf=True)

    await db.commit()


async def _recompute_is_leaf(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    unit: Unit,
) -> None:
    """Recompute is_leaf for a unit based on its children."""
    children_count = await crud.get_unit_children_count(
        db, unit.id, account_id, company_id
    )
    expected_is_leaf = children_count == 0
    if unit.is_leaf != expected_is_leaf:
        await crud.update_unit(db, unit, is_leaf=expected_is_leaf)


async def get_unit_hierarchy(
    db: AsyncSession,
    property_id: int,
    account_id: int,
    company_id: int,
) -> list[UnitHierarchyResponse]:
    """Get the full unit hierarchy for a property.

    Returns a tree structure starting from root units.
    """
    # Get all units for the property
    all_units, _ = await crud.get_units_by_property(
        db, property_id, account_id, company_id, limit=10000
    )

    # Build children lookup
    children_by_parent: dict[int | None, list[Unit]] = {}
    for unit in all_units:
        parent_id = unit.parent_unit_id
        if parent_id not in children_by_parent:
            children_by_parent[parent_id] = []
        children_by_parent[parent_id].append(unit)

    def build_tree(parent_id: int | None) -> list[UnitHierarchyResponse]:
        children = children_by_parent.get(parent_id, [])
        result = []
        for unit in sorted(children, key=lambda u: u.unit_code):
            from .schemas import UnitCategoryResponse

            node = UnitHierarchyResponse(
                id=unit.id,
                uuid=unit.uuid,
                unit_code=unit.unit_code,
                display_name=unit.display_name,
                category=(
                    UnitCategoryResponse.model_validate(unit.category)
                    if unit.category
                    else None
                ),
                is_leaf=unit.is_leaf,
                status=unit.status,
                children=build_tree(unit.id),
            )
            result.append(node)
        return result

    return build_tree(None)


async def get_leasable_units(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    property_id: int | None = None,
    category_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Unit], int]:
    """Get all leasable units for the leasing screen.

    Returns only leaf units with AVAILABLE status.
    This is the main query for contract/lease creation workflows.

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
    return await crud.get_leasable_units(
        db=db,
        account_id=account_id,
        company_id=company_id,
        property_id=property_id,
        category_id=category_id,
        skip=skip,
        limit=limit,
    )


async def get_leaf_units_by_property(
    db: AsyncSession,
    property_id: int,
    account_id: int,
    company_id: int,
    status: str | None = None,
    category_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Unit], int]:
    """Get all leaf units (rentable) for a specific property.

    Args:
        db: Database session
        property_id: Property ID
        account_id: Account ID
        company_id: Company ID
        status: Optional status filter (UnitStatus value)
        category_id: Optional category filter
        skip: Pagination offset
        limit: Pagination limit

    Returns:
        Tuple of (list of leaf units, total count)
    """
    from .models import UnitStatus

    unit_status = None
    if status:
        try:
            unit_status = UnitStatus(status)
        except ValueError:
            pass  # Invalid status, ignore filter

    return await crud.get_leaf_units(
        db=db,
        property_id=property_id,
        account_id=account_id,
        company_id=company_id,
        status=unit_status,
        category_id=category_id,
        skip=skip,
        limit=limit,
    )


async def _compute_unit_full_path(
    db: AsyncSession,
    unit: "Unit",
    account_id: int,
    company_id: int,
) -> str:
    """Compute the full breadcrumb path for a unit.

    Returns a string like: "Property Name → Parent Unit → Child Unit → This Unit"
    """
    path_parts = []

    # Add the unit itself
    path_parts.append(unit.display_name or unit.unit_code)

    # Traverse up the parent chain
    current_parent_id = unit.parent_unit_id
    while current_parent_id is not None:
        parent = await crud.get_unit_by_id(
            db, current_parent_id, account_id, company_id
        )
        if parent is None:
            break
        path_parts.append(parent.display_name or parent.unit_code)
        current_parent_id = parent.parent_unit_id

    # Add property name at the beginning
    if unit.property:
        path_parts.append(unit.property.property_name)

    # Reverse to get root-to-leaf order
    path_parts.reverse()

    return " → ".join(path_parts)


async def get_leasable_units_for_leasing(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    property_id: int | None = None,
    category_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[dict], int]:
    """Get leasable units with enhanced response for leasing screen.

    Returns leaf units with AVAILABLE status, including:
    - Nested property summary
    - Nested category summary
    - Computed full_path breadcrumb

    Args:
        db: Database session
        account_id: Account ID
        company_id: Company ID
        property_id: Optional property filter
        category_id: Optional category filter
        skip: Pagination offset
        limit: Pagination limit

    Returns:
        Tuple of (list of LeafUnitResponse dicts, total count)
    """
    from .schemas import CategorySummary, LeafUnitResponse, PropertySummary

    # Get raw units from CRUD
    units, total = await crud.get_leasable_units(
        db=db,
        account_id=account_id,
        company_id=company_id,
        property_id=property_id,
        category_id=category_id,
        skip=skip,
        limit=limit,
    )

    # Transform to LeafUnitResponse with computed full_path
    result = []
    for unit in units:
        full_path = await _compute_unit_full_path(db, unit, account_id, company_id)

        leaf_response = LeafUnitResponse(
            id=unit.id,
            uuid=unit.uuid,
            unit_code=unit.unit_code,
            display_name=unit.display_name,
            full_path=full_path,
            property=PropertySummary(
                id=unit.property.id,
                uuid=unit.property.uuid,
                property_code=unit.property.property_code,
                property_name=unit.property.property_name,
                usage_type=unit.property.usage_type.value,
            ),
            category=CategorySummary(
                id=unit.category.id,
                code=unit.category.code,
                name=unit.category.name,
                is_residential=unit.category.is_residential,
                is_commercial=unit.category.is_commercial,
            ),
            status=unit.status,
            capacity=unit.capacity,
            area_sqm=float(unit.area_sqm) if unit.area_sqm else None,
            floor_number=unit.floor_number,
            room_number=unit.room_number,
        )
        result.append(leaf_response)

    return result, total
