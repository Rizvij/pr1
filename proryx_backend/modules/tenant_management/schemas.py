"""Tenant management schemas for ProRyx.

Per EP-03 specification.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .models import (
    ContactStatus,
    DocumentCategory,
    DocumentVerificationStatus,
    Gender,
    KYCStatus,
    TenantStatus,
    TenantType,
)

# ----- Document Type Schemas -----


class DocumentTypeBase(BaseModel):
    """Base document type schema per EP-03 spec section 2.4."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = None
    document_category: DocumentCategory | None = None
    applicable_to: TenantType | None = None  # None = applies to both
    is_mandatory: bool = False
    is_expiry_required: bool = False
    sort_order: int = 0


class DocumentTypeCreate(DocumentTypeBase):
    """Schema for creating a document type."""

    pass


class DocumentTypeResponse(DocumentTypeBase):
    """Schema for document type response."""

    id: int
    is_active: bool

    class Config:
        from_attributes = True


# ----- Tenant Schemas -----


class TenantBase(BaseModel):
    """Base tenant schema per EP-03 spec section 2.1."""

    tenant_code: str = Field(..., min_length=1, max_length=50)
    tenant_type: TenantType = TenantType.INDIVIDUAL
    # Contact info
    primary_email: str | None = Field(None, max_length=255)
    primary_phone: str | None = Field(None, max_length=50)
    mobile: str | None = Field(None, max_length=50)
    address_line_1: str | None = Field(None, max_length=255)
    address_line_2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=120)
    country: str | None = Field(None, max_length=120)
    notes: str | None = None


class TenantIndividualCreate(TenantBase):
    """Schema for creating an individual tenant per EP-03 spec."""

    tenant_type: TenantType = TenantType.INDIVIDUAL
    first_name: str = Field(..., min_length=1, max_length=120)
    last_name: str = Field(..., min_length=1, max_length=120)  # Required per spec
    date_of_birth: date | None = None
    gender: Gender | None = None
    nationality: str | None = Field(None, max_length=100)
    passport_number: str | None = Field(None, max_length=50)
    emirates_id: str | None = Field(None, max_length=50)
    occupation: str | None = Field(None, max_length=120)
    employer_name: str | None = Field(None, max_length=255)
    # Emergency contact
    emergency_contact_name: str | None = Field(None, max_length=255)
    emergency_contact_phone: str | None = Field(None, max_length=50)
    preferred_language: str | None = Field(None, max_length=10)
    source: str | None = Field(None, max_length=120)


class TenantEntityCreate(TenantBase):
    """Schema for creating an entity tenant per EP-03 spec."""

    tenant_type: TenantType = TenantType.ENTITY
    entity_name: str = Field(..., min_length=1, max_length=255)
    trade_name: str | None = Field(None, max_length=255)
    trade_license_number: str | None = Field(None, max_length=100)
    registration_number: str | None = Field(None, max_length=100)
    # Emergency contact
    emergency_contact_name: str | None = Field(None, max_length=255)
    emergency_contact_phone: str | None = Field(None, max_length=50)
    preferred_language: str | None = Field(None, max_length=10)
    source: str | None = Field(None, max_length=120)


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""

    tenant_code: str | None = Field(None, min_length=1, max_length=50)
    # Individual fields
    first_name: str | None = Field(None, min_length=1, max_length=120)
    last_name: str | None = Field(None, max_length=120)
    date_of_birth: date | None = None
    gender: Gender | None = None
    nationality: str | None = Field(None, max_length=100)
    passport_number: str | None = Field(None, max_length=50)
    emirates_id: str | None = Field(None, max_length=50)
    occupation: str | None = Field(None, max_length=120)
    employer_name: str | None = Field(None, max_length=255)
    # Entity fields
    entity_name: str | None = Field(None, min_length=1, max_length=255)
    trade_name: str | None = Field(None, max_length=255)
    trade_license_number: str | None = Field(None, max_length=100)
    registration_number: str | None = Field(None, max_length=100)
    # Contact info
    primary_email: str | None = Field(None, max_length=255)
    primary_phone: str | None = Field(None, max_length=50)
    mobile: str | None = Field(None, max_length=50)
    address_line_1: str | None = Field(None, max_length=255)
    address_line_2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=120)
    country: str | None = Field(None, max_length=120)
    # Emergency contact
    emergency_contact_name: str | None = Field(None, max_length=255)
    emergency_contact_phone: str | None = Field(None, max_length=50)
    preferred_language: str | None = Field(None, max_length=10)
    source: str | None = Field(None, max_length=120)
    status: TenantStatus | None = None
    notes: str | None = None


class TenantResponse(TenantBase):
    """Schema for tenant response."""

    id: int
    uuid: UUID
    account_id: int
    company_id: int
    # Individual fields
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None  # Computed/stored per spec
    date_of_birth: date | None = None
    gender: Gender | None = None
    nationality: str | None = None
    passport_number: str | None = None
    emirates_id: str | None = None
    occupation: str | None = None
    employer_name: str | None = None
    # Entity fields
    entity_name: str | None = None
    trade_name: str | None = None
    trade_license_number: str | None = None
    registration_number: str | None = None
    # Emergency contact
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    preferred_language: str | None = None
    source: str | None = None
    # KYC
    kyc_status: KYCStatus
    kyc_verified_at: datetime | None = None
    kyc_verified_by_id: int | None = None
    next_doc_expiry_date: date | None = None
    # Status
    status: TenantStatus
    # Blacklist fields
    blacklist_reason: str | None = None
    blacklisted_at: datetime | None = None
    blacklisted_by_id: int | None = None
    # Counts
    active_contracts_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class TenantSummary(BaseModel):
    """Tenant summary for list views."""

    id: int
    uuid: UUID
    tenant_code: str
    tenant_type: TenantType
    full_name: str | None = None
    display_name: str
    kyc_status: KYCStatus
    status: TenantStatus

    class Config:
        from_attributes = True


class TenantWithDetails(TenantResponse):
    """Tenant with contacts and documents."""

    contacts: list["TenantContactResponse"] = []
    documents: list["TenantDocumentResponse"] = []


# ----- Tenant Contact Schemas -----


class TenantContactBase(BaseModel):
    """Base tenant contact schema per EP-03 spec section 2.3."""

    contact_name: str = Field(..., min_length=1, max_length=255)
    role: str | None = Field(None, max_length=120)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    mobile: str | None = Field(None, max_length=50)
    is_primary: bool = False
    status: ContactStatus = ContactStatus.ACTIVE
    notes: str | None = None


class TenantContactCreate(TenantContactBase):
    """Schema for creating a tenant contact."""

    pass


class TenantContactUpdate(BaseModel):
    """Schema for updating a tenant contact."""

    contact_name: str | None = Field(None, min_length=1, max_length=255)
    role: str | None = Field(None, max_length=120)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    mobile: str | None = Field(None, max_length=50)
    is_primary: bool | None = None
    status: ContactStatus | None = None
    notes: str | None = None


class TenantContactResponse(TenantContactBase):
    """Schema for tenant contact response."""

    id: int
    uuid: UUID
    account_id: int
    company_id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# ----- Tenant Document Schemas -----


class TenantDocumentBase(BaseModel):
    """Base tenant document schema per EP-03 spec section 2.5."""

    document_type_id: int
    document_number: str | None = Field(None, max_length=100)
    issue_date: date | None = None
    expiry_date: date | None = None
    issuing_authority: str | None = Field(None, max_length=255)
    issuing_country: str | None = Field(None, max_length=120)
    notes: str | None = None


class TenantDocumentCreate(TenantDocumentBase):
    """Schema for creating a tenant document."""

    pass


class TenantDocumentUpdate(BaseModel):
    """Schema for updating a tenant document."""

    document_number: str | None = Field(None, max_length=100)
    issue_date: date | None = None
    expiry_date: date | None = None
    issuing_authority: str | None = Field(None, max_length=255)
    issuing_country: str | None = Field(None, max_length=120)
    notes: str | None = None


class TenantDocumentResponse(TenantDocumentBase):
    """Schema for tenant document response."""

    id: int
    uuid: UUID
    account_id: int
    company_id: int
    tenant_id: int
    document_type: DocumentTypeResponse | None = None
    file_reference: str | None = None
    file_name: str | None = None
    file_size_kb: int | None = None
    file_type: str | None = None
    verification_status: DocumentVerificationStatus
    verified_at: datetime | None = None
    verified_by_id: int | None = None
    rejection_reason: str | None = None
    is_primary: bool = False
    is_expired: bool = False
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# ----- Verification Schemas -----


class DocumentVerifyRequest(BaseModel):
    """Request to verify a document."""

    pass


class DocumentRejectRequest(BaseModel):
    """Request to reject a document."""

    reason: str = Field(..., min_length=1, max_length=500)


class KYCUpdateRequest(BaseModel):
    """Request to update KYC status."""

    kyc_status: KYCStatus


class TenantBlacklistRequest(BaseModel):
    """Request to blacklist a tenant per EP-03 spec."""

    reason: str = Field(..., min_length=1, max_length=500)


# Update forward references
TenantWithDetails.model_rebuild()
