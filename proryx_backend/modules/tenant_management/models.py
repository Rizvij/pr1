"""Tenant management models for ProRyx.

EP-03: Tenant Management & KYC
- Tenants (individuals and entities)
- KYC documents and verification
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...database import AccountScoped, Base, TimestampMixin


class TenantType(str, enum.Enum):
    """Tenant types."""

    INDIVIDUAL = "individual"
    ENTITY = "entity"  # Company/Organization


class TenantStatus(str, enum.Enum):
    """Tenant status values."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    BLACKLISTED = "blacklisted"


class Gender(str, enum.Enum):
    """Gender values (per EP-03 spec)."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class KYCStatus(str, enum.Enum):
    """KYC verification status (per EP-03 spec)."""

    NOT_STARTED = "not_started"
    INCOMPLETE = "incomplete"
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"
    EXPIRED = "expired"
    REJECTED = "rejected"


class DocumentVerificationStatus(str, enum.Enum):
    """Document verification status (per EP-03 spec)."""

    NOT_UPLOADED = "not_uploaded"
    UPLOADED = "uploaded"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"


class DocumentCategory(str, enum.Enum):
    """Document category values (per EP-03 spec)."""

    IDENTITY = "identity"
    RESIDENCY = "residency"
    BUSINESS = "business"
    FINANCIAL = "financial"
    OTHER = "other"


class DocumentType(Base):
    """Document type lookup table.

    Types: PASSPORT, EMIRATES_ID, TRADE_LICENSE, VISA, etc.
    """

    __tablename__ = "document_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_category: Mapped[DocumentCategory | None] = mapped_column(
        Enum(DocumentCategory), nullable=True
    )
    applicable_to: Mapped[TenantType | None] = mapped_column(
        Enum(TenantType), nullable=True
    )  # None = applicable to both
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_expiry_required: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<DocumentType(code={self.code}, name={self.name})>"


class Tenant(AccountScoped, TimestampMixin, Base):
    """Tenant within account + company scope.

    Represents a renter (individual person or organization).
    Per EP-03 spec section 2.1.
    """

    __tablename__ = "tenants"

    tenant_code: Mapped[str] = mapped_column(String(50), nullable=False)
    tenant_type: Mapped[TenantType] = mapped_column(
        Enum(TenantType), nullable=False, default=TenantType.INDIVIDUAL
    )

    # Individual fields
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    full_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Computed/stored per EP-03 spec
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[Gender | None] = mapped_column(Enum(Gender), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    passport_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    emirates_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    employer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Entity fields
    entity_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trade_license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Contact Information
    primary_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Emergency Contact (per EP-03 spec)
    emergency_contact_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    emergency_contact_phone: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    preferred_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )  # Referral source

    # KYC Status
    kyc_status: Mapped[KYCStatus] = mapped_column(
        Enum(KYCStatus), nullable=False, default=KYCStatus.NOT_STARTED
    )
    kyc_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    kyc_verified_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_doc_expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Status
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus), nullable=False, default=TenantStatus.ACTIVE
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Blacklist fields (per EP-03 spec)
    blacklist_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    blacklisted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    blacklisted_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Denormalized counts (per EP-03 spec)
    active_contracts_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # Relationships
    contacts: Mapped[list["TenantContact"]] = relationship(
        "TenantContact",
        back_populates="tenant",
        cascade="all, delete-orphan",
        foreign_keys="[TenantContact.account_id, TenantContact.company_id, TenantContact.tenant_id]",
    )
    documents: Mapped[list["TenantDocument"]] = relationship(
        "TenantDocument",
        back_populates="tenant",
        cascade="all, delete-orphan",
        foreign_keys="[TenantDocument.account_id, TenantDocument.company_id, TenantDocument.tenant_id]",
    )

    __table_args__ = (
        Index(
            "ix_tenants_code",
            "account_id",
            "company_id",
            "tenant_code",
            unique=True,
        ),
        Index("ix_tenants_type", "account_id", "company_id", "tenant_type"),
        Index("ix_tenants_status", "account_id", "company_id", "status"),
        Index("ix_tenants_kyc_status", "account_id", "company_id", "kyc_status"),
        Index("ix_tenants_passport", "account_id", "company_id", "passport_number"),
        Index("ix_tenants_emirates_id", "account_id", "company_id", "emirates_id"),
    )

    @property
    def display_name(self) -> str:
        """Get display name based on tenant type.

        Returns full_name if set, otherwise computes from first/last name or entity_name.
        """
        if self.full_name:
            return self.full_name
        if self.tenant_type == TenantType.INDIVIDUAL:
            parts = [self.first_name, self.last_name]
            return " ".join(p for p in parts if p) or self.tenant_code
        else:
            return self.entity_name or self.tenant_code

    def __repr__(self) -> str:
        return (
            f"<Tenant(id={self.id}, code={self.tenant_code}, type={self.tenant_type})>"
        )


class ContactStatus(str, enum.Enum):
    """Contact status values (per EP-03 spec)."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class TenantContact(AccountScoped, TimestampMixin, Base):
    """Contact person for a tenant.

    Useful for entity tenants or emergency contacts.
    """

    __tablename__ = "tenant_contacts"

    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )  # e.g., "Manager", "Emergency"
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[ContactStatus] = mapped_column(
        Enum(ContactStatus), nullable=False, default=ContactStatus.ACTIVE
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="contacts",
        foreign_keys="[TenantContact.account_id, TenantContact.company_id, TenantContact.tenant_id]",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "company_id", "tenant_id"],
            ["tenants.account_id", "tenants.company_id", "tenants.id"],
            ondelete="CASCADE",
        ),
        Index("ix_tenant_contacts_tenant", "account_id", "company_id", "tenant_id"),
        Index(
            "ix_tenant_contacts_primary",
            "account_id",
            "company_id",
            "tenant_id",
            "is_primary",
        ),
    )

    def __repr__(self) -> str:
        return f"<TenantContact(id={self.id}, tenant_id={self.tenant_id}, name={self.contact_name})>"


class TenantDocument(AccountScoped, TimestampMixin, Base):
    """Document uploaded for KYC verification."""

    __tablename__ = "tenant_documents"

    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False)
    document_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("document_types.id"), nullable=False
    )
    document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issuing_country: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # File storage (per EP-03 spec)
    file_reference: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # Storage path/reference
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size_kb: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # Size in KB per spec
    file_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # MIME type

    # Verification
    verification_status: Mapped[DocumentVerificationStatus] = mapped_column(
        Enum(DocumentVerificationStatus),
        nullable=False,
        default=DocumentVerificationStatus.NOT_UPLOADED,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="documents",
        foreign_keys="[TenantDocument.account_id, TenantDocument.company_id, TenantDocument.tenant_id]",
    )
    document_type: Mapped["DocumentType"] = relationship("DocumentType")

    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "company_id", "tenant_id"],
            ["tenants.account_id", "tenants.company_id", "tenants.id"],
            ondelete="CASCADE",
        ),
        Index("ix_tenant_documents_tenant", "account_id", "company_id", "tenant_id"),
        Index(
            "ix_tenant_documents_type",
            "account_id",
            "company_id",
            "tenant_id",
            "document_type_id",
        ),
        Index(
            "ix_tenant_documents_status",
            "account_id",
            "company_id",
            "verification_status",
        ),
        Index("ix_tenant_documents_expiry", "account_id", "company_id", "expiry_date"),
    )

    @property
    def is_expired(self) -> bool:
        """Check if document is expired."""
        if self.expiry_date:
            return date.today() > self.expiry_date
        return False

    def __repr__(self) -> str:
        return f"<TenantDocument(id={self.id}, tenant_id={self.tenant_id}, type_id={self.document_type_id})>"
