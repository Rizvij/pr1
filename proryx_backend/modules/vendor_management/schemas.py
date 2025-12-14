"""Vendor management schemas for ProRyx.

Per EP-02 specification.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from .models import (
    BillingCycle,
    CoverageScope,
    EscalationType,
    LeaseStatus,
    LeaseTermReason,
    LeaseTermStatus,
    VendorStatus,
    VendorType,
)

# ----- Vendor Schemas -----


class VendorBase(BaseModel):
    """Base vendor schema per EP-02 spec section 2.1."""

    vendor_code: str = Field(..., min_length=1, max_length=50)
    vendor_name: str = Field(..., min_length=1, max_length=255)
    vendor_type: VendorType = VendorType.INDIVIDUAL
    contact_name: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=50)
    contact_email: str | None = Field(None, max_length=255)
    address_line_1: str | None = Field(None, max_length=255)
    address_line_2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=120)
    country: str | None = Field(None, max_length=120)
    notes: str | None = None


class VendorCreate(VendorBase):
    """Schema for creating a vendor."""

    bank_name: str | None = Field(None, max_length=255)
    bank_account_name: str | None = Field(None, max_length=255)
    bank_account_number: str | None = Field(None, max_length=100)
    bank_iban: str | None = Field(None, max_length=50)
    bank_swift: str | None = Field(None, max_length=20)
    tax_registration_number: str | None = Field(None, max_length=100)
    status: VendorStatus = VendorStatus.ACTIVE


class VendorUpdate(BaseModel):
    """Schema for updating a vendor."""

    vendor_code: str | None = Field(None, min_length=1, max_length=50)
    vendor_name: str | None = Field(None, min_length=1, max_length=255)
    vendor_type: VendorType | None = None
    contact_name: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=50)
    contact_email: str | None = Field(None, max_length=255)
    address_line_1: str | None = Field(None, max_length=255)
    address_line_2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=120)
    country: str | None = Field(None, max_length=120)
    bank_name: str | None = Field(None, max_length=255)
    bank_account_name: str | None = Field(None, max_length=255)
    bank_account_number: str | None = Field(None, max_length=100)
    bank_iban: str | None = Field(None, max_length=50)
    bank_swift: str | None = Field(None, max_length=20)
    tax_registration_number: str | None = Field(None, max_length=100)
    status: VendorStatus | None = None
    notes: str | None = None


class VendorResponse(VendorBase):
    """Schema for vendor response."""

    id: int
    uuid: UUID
    account_id: int
    company_id: int
    bank_name: str | None = None
    bank_account_name: str | None = None
    bank_account_number: str | None = None
    bank_iban: str | None = None
    bank_swift: str | None = None
    tax_registration_number: str | None = None
    active_leases_count: int = 0
    status: VendorStatus
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class VendorSummary(BaseModel):
    """Vendor summary for list views."""

    id: int
    uuid: UUID
    vendor_code: str
    vendor_name: str
    vendor_type: VendorType
    active_leases_count: int = 0
    status: VendorStatus

    class Config:
        from_attributes = True


# ----- Vendor Lease Schemas -----


class VendorLeaseBase(BaseModel):
    """Base vendor lease schema per EP-02 spec section 2.2."""

    lease_code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    start_date: date
    end_date: date
    rent_amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="AED", max_length=3)
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    payment_day: int | None = Field(None, ge=1, le=31)
    security_deposit: Decimal | None = Field(None, ge=0)
    # Escalation settings
    escalation_type: EscalationType = EscalationType.NONE
    escalation_value: Decimal | None = None
    # Renewal settings
    notice_period_days: int | None = Field(None, ge=0)
    auto_renew: bool = False
    notes: str | None = None

    @field_validator("end_date")
    @classmethod
    def end_date_after_start(cls, v, info):
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("End date must be after start date")
        return v


class VendorLeaseCreate(VendorLeaseBase):
    """Schema for creating a vendor lease."""

    vendor_id: int


class VendorLeaseUpdate(BaseModel):
    """Schema for updating a vendor lease."""

    lease_code: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    rent_amount: Decimal | None = Field(None, ge=0)
    currency: str | None = Field(None, max_length=3)
    billing_cycle: BillingCycle | None = None
    payment_day: int | None = Field(None, ge=1, le=31)
    security_deposit: Decimal | None = Field(None, ge=0)
    escalation_type: EscalationType | None = None
    escalation_value: Decimal | None = None
    notice_period_days: int | None = Field(None, ge=0)
    auto_renew: bool | None = None
    notes: str | None = None


class VendorLeaseResponse(VendorLeaseBase):
    """Schema for vendor lease response."""

    id: int
    uuid: UUID
    account_id: int
    company_id: int
    vendor_id: int
    vendor: VendorSummary | None = None
    status: LeaseStatus
    activated_at: datetime | None = None
    # Termination fields
    termination_date: date | None = None
    terminated_at: datetime | None = None
    termination_reason: str | None = None
    terminated_by_id: int | None = None
    # Counts
    total_covered_units: int = 0
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class VendorLeaseWithDetails(VendorLeaseResponse):
    """Vendor lease with terms and coverage."""

    terms: list["VendorLeaseTermResponse"] = []
    coverages: list["VendorLeaseCoverageResponse"] = []


# ----- Vendor Lease Term Schemas -----


class VendorLeaseTermBase(BaseModel):
    """Base vendor lease term schema per EP-02 spec section 2.3."""

    term_number: int = Field(..., ge=1)
    start_date: date
    end_date: date
    rent_amount: Decimal = Field(..., ge=0)
    rent_change_pct: Decimal | None = None
    reason: LeaseTermReason | None = None
    notes: str | None = None


class VendorLeaseTermCreate(VendorLeaseTermBase):
    """Schema for creating a vendor lease term."""

    status: LeaseTermStatus = LeaseTermStatus.ACTIVE


class VendorLeaseTermUpdate(BaseModel):
    """Schema for updating a vendor lease term (FUTURE terms only)."""

    start_date: date | None = None
    end_date: date | None = None
    rent_amount: Decimal | None = Field(None, ge=0)
    rent_change_pct: Decimal | None = None
    reason: LeaseTermReason | None = None
    notes: str | None = None


class VendorLeaseTermResponse(VendorLeaseTermBase):
    """Schema for vendor lease term response."""

    id: int
    uuid: UUID
    account_id: int
    company_id: int
    lease_id: int
    status: LeaseTermStatus
    approved_by_id: int | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# ----- Vendor Lease Coverage Schemas -----


class VendorLeaseCoverageBase(BaseModel):
    """Base vendor lease coverage schema per EP-02 spec section 2.4."""

    scope_type: CoverageScope
    property_id: int | None = None
    unit_id: int | None = None
    covered_from: date | None = None
    covered_to: date | None = None
    rent_allocation: Decimal | None = None
    notes: str | None = Field(None, max_length=500)

    @field_validator("property_id", "unit_id")
    @classmethod
    def validate_scope_ids(cls, v, info):
        # Validation logic handled in service layer
        return v


class VendorLeaseCoverageCreate(VendorLeaseCoverageBase):
    """Schema for creating a vendor lease coverage."""

    pass


class VendorLeaseCoverageResponse(VendorLeaseCoverageBase):
    """Schema for vendor lease coverage response."""

    id: int
    uuid: UUID
    account_id: int
    company_id: int
    lease_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ----- Action Schemas -----


class LeaseActivateRequest(BaseModel):
    """Request to activate a lease."""

    pass


class LeaseTerminateRequest(BaseModel):
    """Request to terminate a lease."""

    reason: str = Field(..., min_length=1, max_length=500)


# Update forward references
VendorLeaseWithDetails.model_rebuild()
