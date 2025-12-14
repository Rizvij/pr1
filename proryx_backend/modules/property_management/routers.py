"""Property management API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ..auth.dependencies import CurrentUser
from ..commons import BaseResponse, PaginatedResponse
from . import crud, services
from .models import PropertyStatus, UnitStatus
from .schemas import (
    LeafUnitResponse,
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
    PropertyWithUnitsResponse,
    UnitCategoryCreate,
    UnitCategoryResponse,
    UnitCreate,
    UnitHierarchyResponse,
    UnitResponse,
    UnitUpdate,
)

router = APIRouter(prefix="/properties", tags=["Properties"])
units_router = APIRouter(prefix="/units", tags=["Units"])
categories_router = APIRouter(prefix="/unit-categories", tags=["Unit Categories"])


# ----- Unit Categories -----


@categories_router.get("", response_model=BaseResponse[list[UnitCategoryResponse]])
async def list_unit_categories(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    is_active: bool | None = Query(None),
):
    """Get all unit categories."""
    categories = await crud.get_all_unit_categories(db, is_active=is_active)
    return BaseResponse(
        success=True,
        data=[UnitCategoryResponse.model_validate(c) for c in categories],
    )


@categories_router.get(
    "/{category_id}", response_model=BaseResponse[UnitCategoryResponse]
)
async def get_unit_category(
    category_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a unit category by ID."""
    category = await crud.get_unit_category_by_id(db, category_id)
    if not category:
        from ...core.exceptions import NotFoundError

        raise NotFoundError(f"Unit category with ID {category_id} not found")
    return BaseResponse(
        success=True,
        data=UnitCategoryResponse.model_validate(category),
    )


@categories_router.post("", response_model=BaseResponse[UnitCategoryResponse])
async def create_unit_category(
    data: UnitCategoryCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new unit category (admin only)."""
    # Check for duplicate code
    existing = await crud.get_unit_category_by_code(db, data.code.upper())
    if existing:
        from ...core.exceptions import ValidationError

        raise ValidationError(f"Category with code '{data.code}' already exists")

    category = await crud.create_unit_category(
        db,
        code=data.code,
        name=data.name,
        description=data.description,
    )
    await db.commit()

    return BaseResponse(
        success=True,
        message="Unit category created successfully",
        data=UnitCategoryResponse.model_validate(category),
    )


# ----- Properties -----


@router.get("", response_model=BaseResponse[PaginatedResponse[PropertyResponse]])
async def list_properties(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: PropertyStatus | None = Query(None),
    usage_type: str | None = Query(None),
    search: str | None = Query(None),
):
    """Get properties with pagination and filtering."""
    skip = (page - 1) * page_size
    properties, total = await crud.get_properties(
        db=db,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        skip=skip,
        limit=page_size,
        status=status,
        usage_type=usage_type,
        search=search,
    )

    return BaseResponse(
        success=True,
        data=PaginatedResponse.from_items(
            items=[PropertyResponse.model_validate(p) for p in properties],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@router.get("/{property_id}", response_model=BaseResponse[PropertyWithUnitsResponse])
async def get_property(
    property_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_units: bool = Query(False),
):
    """Get a property by ID."""
    property_obj = await crud.get_property_by_id(
        db,
        property_id=property_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        include_units=include_units,
    )
    if not property_obj:
        from ...core.exceptions import NotFoundError

        raise NotFoundError(f"Property with ID {property_id} not found")

    return BaseResponse(
        success=True,
        data=PropertyWithUnitsResponse.model_validate(property_obj),
    )


@router.post("", response_model=BaseResponse[PropertyResponse])
async def create_property(
    data: PropertyCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new property."""
    property_obj = await services.create_property(
        db=db,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Property created successfully",
        data=PropertyResponse.model_validate(property_obj),
    )


@router.put("/{property_id}", response_model=BaseResponse[PropertyResponse])
async def update_property(
    property_id: int,
    data: PropertyUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a property."""
    property_obj = await services.update_property(
        db=db,
        property_id=property_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Property updated successfully",
        data=PropertyResponse.model_validate(property_obj),
    )


@router.delete("/{property_id}", response_model=BaseResponse[None])
async def delete_property(
    property_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a property and all its units."""
    await services.delete_property(
        db=db,
        property_id=property_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
    )

    return BaseResponse(
        success=True,
        message="Property deleted successfully",
    )


# ----- Property Units -----


@router.get(
    "/{property_id}/units",
    response_model=BaseResponse[PaginatedResponse[UnitResponse]],
)
async def list_property_units(
    property_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: UnitStatus | None = Query(None),
    is_leaf: bool | None = Query(None),
    parent_unit_id: int | None = Query(None),
):
    """Get units for a property with pagination and filtering."""
    # Verify property exists
    property_obj = await crud.get_property_by_id(
        db, property_id, current_user.account_id, current_user.company_id
    )
    if not property_obj:
        from ...core.exceptions import NotFoundError

        raise NotFoundError(f"Property with ID {property_id} not found")

    skip = (page - 1) * page_size
    units, total = await crud.get_units_by_property(
        db=db,
        property_id=property_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        skip=skip,
        limit=page_size,
        status=status,
        is_leaf=is_leaf,
        parent_unit_id=parent_unit_id,
    )

    return BaseResponse(
        success=True,
        data=PaginatedResponse.from_items(
            items=[UnitResponse.model_validate(u) for u in units],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@router.get(
    "/{property_id}/units/hierarchy",
    response_model=BaseResponse[list[UnitHierarchyResponse]],
)
async def get_property_unit_hierarchy(
    property_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get the full unit hierarchy tree for a property."""
    # Verify property exists
    property_obj = await crud.get_property_by_id(
        db, property_id, current_user.account_id, current_user.company_id
    )
    if not property_obj:
        from ...core.exceptions import NotFoundError

        raise NotFoundError(f"Property with ID {property_id} not found")

    hierarchy = await services.get_unit_hierarchy(
        db=db,
        property_id=property_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
    )

    return BaseResponse(
        success=True,
        data=hierarchy,
    )


# ----- Units (standalone) -----


@units_router.get("/{unit_id}", response_model=BaseResponse[UnitResponse])
async def get_unit(
    unit_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a unit by ID."""
    unit = await crud.get_unit_by_id(
        db,
        unit_id=unit_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
    )
    if not unit:
        from ...core.exceptions import NotFoundError

        raise NotFoundError(f"Unit with ID {unit_id} not found")

    return BaseResponse(
        success=True,
        data=UnitResponse.model_validate(unit),
    )


@units_router.post("", response_model=BaseResponse[UnitResponse])
async def create_unit(
    data: UnitCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new unit."""
    unit = await services.create_unit(
        db=db,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    # Reload to get category relationship
    unit = await crud.get_unit_by_id(
        db, unit.id, current_user.account_id, current_user.company_id
    )

    return BaseResponse(
        success=True,
        message="Unit created successfully",
        data=UnitResponse.model_validate(unit),
    )


@units_router.put("/{unit_id}", response_model=BaseResponse[UnitResponse])
async def update_unit(
    unit_id: int,
    data: UnitUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a unit."""
    unit = await services.update_unit(
        db=db,
        unit_id=unit_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    # Reload to get category relationship
    unit = await crud.get_unit_by_id(
        db, unit.id, current_user.account_id, current_user.company_id
    )

    return BaseResponse(
        success=True,
        message="Unit updated successfully",
        data=UnitResponse.model_validate(unit),
    )


@units_router.delete("/{unit_id}", response_model=BaseResponse[None])
async def delete_unit(
    unit_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a unit."""
    await services.delete_unit(
        db=db,
        unit_id=unit_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
    )

    return BaseResponse(
        success=True,
        message="Unit deleted successfully",
    )


@units_router.get(
    "/{unit_id}/children",
    response_model=BaseResponse[list[UnitResponse]],
)
async def get_unit_children(
    unit_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get direct children of a unit."""
    # Verify unit exists
    unit = await crud.get_unit_by_id(
        db, unit_id, current_user.account_id, current_user.company_id
    )
    if not unit:
        from ...core.exceptions import NotFoundError

        raise NotFoundError(f"Unit with ID {unit_id} not found")

    # Get children
    children, _ = await crud.get_units_by_property(
        db=db,
        property_id=unit.property_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        parent_unit_id=unit_id,
        limit=1000,
    )

    return BaseResponse(
        success=True,
        data=[UnitResponse.model_validate(u) for u in children],
    )


# ----- Leaf Units (for Leasing) -----


@units_router.get("/leaf", response_model=BaseResponse[PaginatedResponse[UnitResponse]])
async def get_leasable_units(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    property_id: int | None = Query(None, description="Filter by property"),
    category_id: int | None = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Get all leasable units for the leasing screen.

    Returns only leaf units with AVAILABLE status.
    This is the main endpoint for contract/lease creation workflows.
    """
    skip = (page - 1) * page_size
    units, total = await services.get_leasable_units(
        db=db,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        property_id=property_id,
        category_id=category_id,
        skip=skip,
        limit=page_size,
    )

    return BaseResponse(
        success=True,
        data=PaginatedResponse.from_items(
            items=[UnitResponse.model_validate(u) for u in units],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@units_router.get(
    "/leasing", response_model=BaseResponse[PaginatedResponse[LeafUnitResponse]]
)
async def get_units_for_leasing(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    property_id: int | None = Query(None, description="Filter by property"),
    category_id: int | None = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Get leasable units for the leasing screen with enhanced response.

    Returns leaf units (is_leaf=True) with AVAILABLE status.
    Includes nested property/category and computed full_path breadcrumb.
    This is the recommended endpoint for the leasing/contract creation UI.
    """
    skip = (page - 1) * page_size
    units, total = await services.get_leasable_units_for_leasing(
        db=db,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        property_id=property_id,
        category_id=category_id,
        skip=skip,
        limit=page_size,
    )

    return BaseResponse(
        success=True,
        data=PaginatedResponse.from_items(
            items=units,
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@router.get(
    "/{property_id}/units/leaf",
    response_model=BaseResponse[PaginatedResponse[UnitResponse]],
)
async def get_property_leaf_units(
    property_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None, description="Filter by status"),
    category_id: int | None = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Get all leaf units (rentable) for a specific property.

    Returns only units with is_leaf=True.
    """
    # Verify property exists
    property_obj = await crud.get_property_by_id(
        db, property_id, current_user.account_id, current_user.company_id
    )
    if not property_obj:
        from ...core.exceptions import NotFoundError

        raise NotFoundError(f"Property with ID {property_id} not found")

    skip = (page - 1) * page_size
    units, total = await services.get_leaf_units_by_property(
        db=db,
        property_id=property_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        status=status,
        category_id=category_id,
        skip=skip,
        limit=page_size,
    )

    return BaseResponse(
        success=True,
        data=PaginatedResponse.from_items(
            items=[UnitResponse.model_validate(u) for u in units],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )
