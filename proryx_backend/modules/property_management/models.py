"""Property management models for ProRyx.

EP-01: Property & Unit Management
- Properties with hierarchical units
- Unit categories as lookup table
"""

import enum

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...database import AccountScoped, Base, TimestampMixin


class PropertyUsageType(str, enum.Enum):
    """Property usage types."""

    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    MIXED = "mixed"


class PropertyStatus(str, enum.Enum):
    """Property status values."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    UNDER_MAINTENANCE = "under_maintenance"


class UnitStatus(str, enum.Enum):
    """Unit status values."""

    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    UNDER_MAINTENANCE = "under_maintenance"
    INACTIVE = "inactive"


class UnitCategory(Base):
    """Unit category lookup table.

    Categories: APARTMENT, BEDSPACE, SHOP, OFFICE, WAREHOUSE, PARKING, etc.
    Per EP-01 spec section 2.3.
    """

    __tablename__ = "unit_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_residential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_commercial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allowed_parent_categories: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON array of valid parent category codes
    max_depth: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<UnitCategory(code={self.code}, name={self.name})>"


class Property(AccountScoped, TimestampMixin, Base):
    """Property within account + company scope.

    Represents a building or complex that contains units.
    Per EP-01 spec section 2.1.
    """

    __tablename__ = "properties"

    property_code: Mapped[str] = mapped_column(String(50), nullable=False)
    property_name: Mapped[str] = mapped_column(String(255), nullable=False)
    usage_type: Mapped[PropertyUsageType] = mapped_column(
        Enum(PropertyUsageType), nullable=False, default=PropertyUsageType.RESIDENTIAL
    )
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    latitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    total_floors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_units_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_units_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[PropertyStatus] = mapped_column(
        Enum(PropertyStatus), nullable=False, default=PropertyStatus.ACTIVE
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    units: Mapped[list["Unit"]] = relationship(
        "Unit",
        back_populates="property",
        cascade="all, delete-orphan",
        foreign_keys="[Unit.account_id, Unit.company_id, Unit.property_id]",
    )

    __table_args__ = (
        Index(
            "ix_properties_code",
            "account_id",
            "company_id",
            "property_code",
            unique=True,
        ),
        Index("ix_properties_status", "account_id", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Property(id={self.id}, code={self.property_code}, name={self.property_name})>"


class Unit(AccountScoped, TimestampMixin, Base):
    """Unit within a property.

    Units can be hierarchical (e.g., Floor -> Apartment -> Bedroom).
    Use parent_unit_id for hierarchy. is_leaf indicates rentable units.
    Per EP-01 spec section 2.2.
    """

    __tablename__ = "units"

    property_id: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_unit_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_code: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("unit_categories.id"), nullable=False
    )
    floor_number: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # Per spec: VARCHAR(10)
    room_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    area_sqm: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_leaf: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[UnitStatus] = mapped_column(
        Enum(UnitStatus), nullable=False, default=UnitStatus.AVAILABLE
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    category: Mapped["UnitCategory"] = relationship("UnitCategory")
    property: Mapped["Property"] = relationship(
        "Property",
        back_populates="units",
        foreign_keys="[Unit.account_id, Unit.company_id, Unit.property_id]",
    )
    # Note: Self-referencing parent/children relationships removed due to composite key complexity
    # Parent-child hierarchy handled at application/service level via parent_unit_id column

    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "company_id", "property_id"],
            ["properties.account_id", "properties.company_id", "properties.id"],
            ondelete="CASCADE",
        ),
        # Note: Self-referencing FK removed - MySQL doesn't support SET NULL on NOT NULL columns
        # Parent relationships are handled at application level
        Index(
            "ix_units_code",
            "account_id",
            "company_id",
            "property_id",
            "unit_code",
            unique=True,
        ),
        Index("ix_units_property", "account_id", "company_id", "property_id"),
        Index("ix_units_parent", "account_id", "company_id", "parent_unit_id"),
        Index("ix_units_status", "account_id", "company_id", "status"),
        Index("ix_units_is_leaf", "account_id", "company_id", "is_leaf"),
    )

    def __repr__(self) -> str:
        return f"<Unit(id={self.id}, code={self.unit_code}, name={self.display_name})>"
