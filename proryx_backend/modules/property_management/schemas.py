"""Property management schemas for ProRyx.

Per EP-01 specification.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .models import PropertyStatus, PropertyUsageType, UnitStatus

# ----- Unit Category Schemas -----


class UnitCategoryBase(BaseModel):
    """Base unit category schema per EP-01 spec section 2.3."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = None
    is_residential: bool = False
    is_commercial: bool = False
    allowed_parent_categories: str | None = None  # JSON array of category codes
    max_depth: int = Field(default=1, ge=1)


class UnitCategoryCreate(UnitCategoryBase):
    """Schema for creating a unit category."""

    pass


class UnitCategoryUpdate(BaseModel):
    """Schema for updating a unit category."""

    name: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = None
    is_residential: bool | None = None
    is_commercial: bool | None = None
    allowed_parent_categories: str | None = None
    max_depth: int | None = Field(None, ge=1)
    is_active: bool | None = None


class UnitCategoryResponse(UnitCategoryBase):
    """Schema for unit category response."""

    id: int
    is_active: bool

    class Config:
        from_attributes = True


# ----- Property Schemas -----


class PropertyBase(BaseModel):
    """Base property schema per EP-01 spec section 2.1."""

    property_code: str = Field(..., min_length=1, max_length=50)
    property_name: str = Field(..., min_length=1, max_length=255)
    usage_type: PropertyUsageType = PropertyUsageType.RESIDENTIAL
    address_line_1: str | None = Field(None, max_length=255)
    address_line_2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=120)
    state: str | None = Field(None, max_length=120)
    country: str | None = Field(None, max_length=120)
    postal_code: str | None = Field(None, max_length=20)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    total_floors: int | None = Field(None, ge=0)
    year_built: int | None = Field(None, ge=1800, le=2100)
    notes: str | None = None


class PropertyCreate(PropertyBase):
    """Schema for creating a property."""

    status: PropertyStatus = PropertyStatus.ACTIVE


class PropertyUpdate(BaseModel):
    """Schema for updating a property."""

    property_code: str | None = Field(None, min_length=1, max_length=50)
    property_name: str | None = Field(None, min_length=1, max_length=255)
    usage_type: PropertyUsageType | None = None
    address_line_1: str | None = Field(None, min_length=1, max_length=255)
    address_line_2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=120)
    state: str | None = Field(None, max_length=120)
    country: str | None = Field(None, max_length=120)
    postal_code: str | None = Field(None, max_length=20)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    total_floors: int | None = Field(None, ge=0)
    year_built: int | None = Field(None, ge=1800, le=2100)
    status: PropertyStatus | None = None
    notes: str | None = None


class PropertyResponse(PropertyBase):
    """Schema for property response."""

    id: int
    uuid: UUID
    account_id: int
    company_id: int
    status: PropertyStatus
    total_units_count: int = 0
    active_units_count: int = 0
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class PropertyWithUnitsResponse(PropertyResponse):
    """Property response with units included."""

    units: list["UnitResponse"] = []


# ----- Unit Schemas -----


class UnitBase(BaseModel):
    """Base unit schema per EP-01 spec section 2.2."""

    unit_code: str = Field(..., min_length=1, max_length=50)
    display_name: str | None = Field(None, max_length=255)
    category_id: int
    floor_number: str | None = Field(None, max_length=10)
    room_number: str | None = Field(None, max_length=20)
    area_sqm: float | None = Field(None, ge=0)
    capacity: int = Field(default=1, ge=1)
    sort_order: int = Field(default=0, ge=0)
    notes: str | None = None


class UnitCreate(UnitBase):
    """Schema for creating a unit."""

    property_id: int
    parent_unit_id: int | None = None
    is_leaf: bool = True
    status: UnitStatus = UnitStatus.AVAILABLE


class UnitUpdate(BaseModel):
    """Schema for updating a unit."""

    unit_code: str | None = Field(None, min_length=1, max_length=50)
    display_name: str | None = Field(None, max_length=255)
    category_id: int | None = None
    parent_unit_id: int | None = None
    floor_number: str | None = Field(None, max_length=10)
    room_number: str | None = Field(None, max_length=20)
    area_sqm: float | None = Field(None, ge=0)
    capacity: int | None = Field(None, ge=1)
    sort_order: int | None = Field(None, ge=0)
    is_leaf: bool | None = None
    status: UnitStatus | None = None
    notes: str | None = None


class UnitResponse(UnitBase):
    """Schema for unit response."""

    id: int
    uuid: UUID
    account_id: int
    company_id: int
    property_id: int
    parent_unit_id: int | None
    is_leaf: bool
    status: UnitStatus
    category: UnitCategoryResponse | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class UnitWithChildrenResponse(UnitResponse):
    """Unit response with children included."""

    children: list["UnitResponse"] = []


class UnitHierarchyResponse(BaseModel):
    """Unit hierarchy tree response."""

    id: int
    uuid: UUID
    unit_code: str
    display_name: str | None = None
    category: UnitCategoryResponse | None = None
    is_leaf: bool
    status: UnitStatus
    children: list["UnitHierarchyResponse"] = []

    class Config:
        from_attributes = True


# ----- Leasing Screen Schemas -----


class PropertySummary(BaseModel):
    """Minimal property info for leasing screen."""

    id: int
    uuid: UUID
    property_code: str
    property_name: str
    usage_type: str

    class Config:
        from_attributes = True


class CategorySummary(BaseModel):
    """Minimal category info for leasing screen."""

    id: int
    code: str
    name: str
    is_residential: bool
    is_commercial: bool

    class Config:
        from_attributes = True


class LeafUnitResponse(BaseModel):
    """Enhanced unit response for leasing screen.

    Includes nested property and category, plus computed full_path.
    Only used for leaf units (rentable inventory).
    """

    id: int
    uuid: UUID
    unit_code: str
    display_name: str | None = None
    full_path: str  # Pre-computed breadcrumb: "Property → Parent → Unit"
    property: PropertySummary
    category: CategorySummary
    status: UnitStatus
    capacity: int = 1
    area_sqm: float | None = None
    floor_number: str | None = None
    room_number: str | None = None

    class Config:
        from_attributes = True


# Update forward references
PropertyWithUnitsResponse.model_rebuild()
UnitWithChildrenResponse.model_rebuild()
UnitHierarchyResponse.model_rebuild()
