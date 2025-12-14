"""Vendor management models for ProRyx.

EP-02: Vendor & Vendor Lease Management
- Vendors (property managers, service providers)
- Vendor Leases with terms and coverage
"""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...database import AccountScoped, Base, TimestampMixin


class VendorType(str, enum.Enum):
    """Vendor types per EP-02 spec."""

    INDIVIDUAL = "individual"
    COMPANY = "company"


class VendorStatus(str, enum.Enum):
    """Vendor status values."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class LeaseStatus(str, enum.Enum):
    """Vendor lease status values."""

    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    RENEWED = "renewed"


class BillingCycle(str, enum.Enum):
    """Billing cycle options."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"


class EscalationType(str, enum.Enum):
    """Rent escalation types (per EP-02 spec)."""

    NONE = "none"
    FIXED_AMOUNT = "fixed_amount"
    PERCENTAGE = "percentage"
    CPI_LINKED = "cpi_linked"


class CoverageScope(str, enum.Enum):
    """Coverage scope types."""

    PROPERTY = "property"  # Entire property
    UNIT = "unit"  # Specific unit


class LeaseTermStatus(str, enum.Enum):
    """Lease term status per EP-02 spec."""

    ACTIVE = "active"
    EXPIRED = "expired"
    FUTURE = "future"


class LeaseTermReason(str, enum.Enum):
    """Lease term reason per EP-02 spec."""

    INITIAL = "initial"
    RENEWAL = "renewal"
    AMENDMENT = "amendment"


class Vendor(AccountScoped, TimestampMixin, Base):
    """Vendor within account + company scope.

    Represents landlords/property owners who lease to ProRyx.
    Per EP-02 spec section 2.1.
    """

    __tablename__ = "vendors"

    vendor_code: Mapped[str] = mapped_column(String(50), nullable=False)
    vendor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_type: Mapped[VendorType] = mapped_column(
        Enum(VendorType), nullable=False, default=VendorType.INDIVIDUAL
    )
    # Contact Information
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Bank Details
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_account_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bank_iban: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bank_swift: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Tax Information
    tax_registration_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    # Status & Counts
    active_leases_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[VendorStatus] = mapped_column(
        Enum(VendorStatus), nullable=False, default=VendorStatus.ACTIVE
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    leases: Mapped[list["VendorLease"]] = relationship(
        "VendorLease",
        back_populates="vendor",
        cascade="all, delete-orphan",
        foreign_keys="[VendorLease.account_id, VendorLease.company_id, VendorLease.vendor_id]",
    )

    __table_args__ = (
        Index(
            "ix_vendors_code",
            "account_id",
            "company_id",
            "vendor_code",
            unique=True,
        ),
        Index("ix_vendors_type", "account_id", "company_id", "vendor_type"),
        Index("ix_vendors_status", "account_id", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<Vendor(id={self.id}, code={self.vendor_code}, name={self.vendor_name})>"
        )


class VendorLease(AccountScoped, TimestampMixin, Base):
    """Vendor lease agreement.

    Represents a lease contract between the company and a vendor.
    """

    __tablename__ = "vendor_leases"

    vendor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    lease_code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Financial
    rent_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=0
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AED")
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        Enum(BillingCycle), nullable=False, default=BillingCycle.MONTHLY
    )
    payment_day: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # Day of month (1-31)
    security_deposit: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    # Escalation settings (per EP-02 spec)
    escalation_type: Mapped[EscalationType] = mapped_column(
        Enum(EscalationType), nullable=False, default=EscalationType.NONE
    )
    escalation_value: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )  # Fixed amount or percentage

    # Renewal settings (per EP-02 spec)
    notice_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Status
    status: Mapped[LeaseStatus] = mapped_column(
        Enum(LeaseStatus), nullable=False, default=LeaseStatus.DRAFT
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Termination fields (per EP-02 spec)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    terminated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    termination_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    terminated_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Denormalized counts (per EP-02 spec)
    total_covered_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    vendor: Mapped["Vendor"] = relationship(
        "Vendor",
        back_populates="leases",
        foreign_keys="[VendorLease.account_id, VendorLease.company_id, VendorLease.vendor_id]",
    )
    terms: Mapped[list["VendorLeaseTerm"]] = relationship(
        "VendorLeaseTerm",
        back_populates="lease",
        cascade="all, delete-orphan",
        foreign_keys="[VendorLeaseTerm.account_id, VendorLeaseTerm.company_id, VendorLeaseTerm.lease_id]",
    )
    coverages: Mapped[list["VendorLeaseCoverage"]] = relationship(
        "VendorLeaseCoverage",
        back_populates="lease",
        cascade="all, delete-orphan",
        foreign_keys="[VendorLeaseCoverage.account_id, VendorLeaseCoverage.company_id, VendorLeaseCoverage.lease_id]",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "company_id", "vendor_id"],
            ["vendors.account_id", "vendors.company_id", "vendors.id"],
            ondelete="CASCADE",
        ),
        Index(
            "ix_vendor_leases_code",
            "account_id",
            "company_id",
            "lease_code",
            unique=True,
        ),
        Index("ix_vendor_leases_vendor", "account_id", "company_id", "vendor_id"),
        Index("ix_vendor_leases_status", "account_id", "company_id", "status"),
        Index(
            "ix_vendor_leases_dates",
            "account_id",
            "company_id",
            "start_date",
            "end_date",
        ),
    )

    def __repr__(self) -> str:
        return f"<VendorLease(id={self.id}, code={self.lease_code}, vendor_id={self.vendor_id})>"


class VendorLeaseTerm(AccountScoped, TimestampMixin, Base):
    """Vendor lease term (renewal/modification history).

    Each term represents a period with specific rent conditions.
    Per EP-02 spec section 2.3.
    """

    __tablename__ = "vendor_lease_terms"

    lease_id: Mapped[int] = mapped_column(Integer, nullable=False)
    term_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    rent_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    rent_change_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # Percentage change from previous term
    reason: Mapped[LeaseTermReason | None] = mapped_column(
        Enum(LeaseTermReason), nullable=True
    )  # INITIAL, RENEWAL, AMENDMENT
    status: Mapped[LeaseTermStatus] = mapped_column(
        Enum(LeaseTermStatus), nullable=False, default=LeaseTermStatus.ACTIVE
    )

    # Approval fields (per EP-02 spec)
    approved_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    lease: Mapped["VendorLease"] = relationship(
        "VendorLease",
        back_populates="terms",
        foreign_keys="[VendorLeaseTerm.account_id, VendorLeaseTerm.company_id, VendorLeaseTerm.lease_id]",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "company_id", "lease_id"],
            [
                "vendor_leases.account_id",
                "vendor_leases.company_id",
                "vendor_leases.id",
            ],
            ondelete="CASCADE",
        ),
        Index("ix_vendor_lease_terms_lease", "account_id", "company_id", "lease_id"),
        Index(
            "ix_vendor_lease_terms_unique",
            "account_id",
            "company_id",
            "lease_id",
            "term_number",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<VendorLeaseTerm(id={self.id}, lease_id={self.lease_id}, term={self.term_number})>"


class VendorLeaseCoverage(AccountScoped, TimestampMixin, Base):
    """Vendor lease coverage - which properties/units the lease covers.

    Links a lease to specific properties or units.
    Per EP-02 spec section 2.4.
    """

    __tablename__ = "vendor_lease_coverages"

    lease_id: Mapped[int] = mapped_column(Integer, nullable=False)
    scope_type: Mapped[CoverageScope] = mapped_column(
        Enum(CoverageScope), nullable=False
    )
    property_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Coverage date range (per EP-02 spec)
    covered_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    covered_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    rent_allocation: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )  # Portion of total rent allocated to this coverage
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    lease: Mapped["VendorLease"] = relationship(
        "VendorLease",
        back_populates="coverages",
        foreign_keys="[VendorLeaseCoverage.account_id, VendorLeaseCoverage.company_id, VendorLeaseCoverage.lease_id]",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "company_id", "lease_id"],
            [
                "vendor_leases.account_id",
                "vendor_leases.company_id",
                "vendor_leases.id",
            ],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["account_id", "company_id", "property_id"],
            ["properties.account_id", "properties.company_id", "properties.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["account_id", "company_id", "unit_id"],
            ["units.account_id", "units.company_id", "units.id"],
            ondelete="CASCADE",
        ),
        Index(
            "ix_vendor_lease_coverages_lease", "account_id", "company_id", "lease_id"
        ),
        Index(
            "ix_vendor_lease_coverages_property",
            "account_id",
            "company_id",
            "property_id",
        ),
        Index("ix_vendor_lease_coverages_unit", "account_id", "company_id", "unit_id"),
    )

    def __repr__(self) -> str:
        return f"<VendorLeaseCoverage(id={self.id}, lease_id={self.lease_id}, scope={self.scope_type})>"
