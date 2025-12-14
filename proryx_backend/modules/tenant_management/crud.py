"""CRUD operations for tenant management module."""

from datetime import date, datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    DocumentType,
    DocumentVerificationStatus,
    KYCStatus,
    Tenant,
    TenantContact,
    TenantDocument,
    TenantStatus,
    TenantType,
)

# ----- Document Type CRUD -----


async def get_document_type_by_id(
    db: AsyncSession, doc_type_id: int
) -> DocumentType | None:
    """Get a document type by ID."""
    result = await db.execute(
        select(DocumentType).where(DocumentType.id == doc_type_id)
    )
    return result.scalar_one_or_none()


async def get_document_type_by_code(db: AsyncSession, code: str) -> DocumentType | None:
    """Get a document type by code."""
    result = await db.execute(select(DocumentType).where(DocumentType.code == code))
    return result.scalar_one_or_none()


async def get_all_document_types(
    db: AsyncSession,
    is_active: bool | None = None,
    applicable_to: TenantType | None = None,
) -> list[DocumentType]:
    """Get all document types."""
    query = select(DocumentType)
    if is_active is not None:
        query = query.where(DocumentType.is_active == is_active)
    if applicable_to:
        query = query.where(
            (DocumentType.applicable_to == applicable_to)
            | (DocumentType.applicable_to.is_(None))
        )
    result = await db.execute(query.order_by(DocumentType.name))
    return list(result.scalars().all())


async def create_document_type(
    db: AsyncSession,
    code: str,
    name: str,
    description: str | None = None,
    applicable_to: TenantType | None = None,
    is_mandatory: bool = False,
) -> DocumentType:
    """Create a new document type."""
    doc_type = DocumentType(
        code=code.upper(),
        name=name,
        description=description,
        applicable_to=applicable_to,
        is_mandatory=is_mandatory,
        is_active=True,
    )
    db.add(doc_type)
    await db.flush()
    return doc_type


# ----- Tenant CRUD -----


async def get_tenant_by_id(
    db: AsyncSession,
    tenant_id: int,
    account_id: int,
    company_id: int,
    include_details: bool = False,
) -> Tenant | None:
    """Get a tenant by ID within tenant scope."""
    query = select(Tenant).where(
        and_(
            Tenant.id == tenant_id,
            Tenant.account_id == account_id,
            Tenant.company_id == company_id,
        )
    )
    if include_details:
        query = query.options(
            selectinload(Tenant.contacts),
            selectinload(Tenant.documents).selectinload(TenantDocument.document_type),
        )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_tenant_by_code(
    db: AsyncSession,
    tenant_code: str,
    account_id: int,
    company_id: int,
) -> Tenant | None:
    """Get a tenant by code within tenant scope."""
    result = await db.execute(
        select(Tenant).where(
            and_(
                Tenant.tenant_code == tenant_code,
                Tenant.account_id == account_id,
                Tenant.company_id == company_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_tenants(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    skip: int = 0,
    limit: int = 100,
    tenant_type: TenantType | None = None,
    status: TenantStatus | None = None,
    kyc_status: KYCStatus | None = None,
    search: str | None = None,
) -> tuple[list[Tenant], int]:
    """Get tenants with filtering and pagination."""
    base_filter = and_(
        Tenant.account_id == account_id,
        Tenant.company_id == company_id,
    )

    filters = [base_filter]
    if tenant_type:
        filters.append(Tenant.tenant_type == tenant_type)
    if status:
        filters.append(Tenant.status == status)
    if kyc_status:
        filters.append(Tenant.kyc_status == kyc_status)
    if search:
        search_filter = f"%{search}%"
        filters.append(
            (Tenant.tenant_code.ilike(search_filter))
            | (Tenant.first_name.ilike(search_filter))
            | (Tenant.last_name.ilike(search_filter))
            | (Tenant.entity_name.ilike(search_filter))
            | (Tenant.email.ilike(search_filter))
            | (Tenant.passport_number.ilike(search_filter))
            | (Tenant.emirates_id.ilike(search_filter))
        )

    # Count query
    count_query = select(func.count(Tenant.id)).where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Data query
    data_query = (
        select(Tenant)
        .where(and_(*filters))
        .order_by(Tenant.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(data_query)
    tenants = list(result.scalars().all())

    return tenants, total


async def create_tenant(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    tenant_code: str,
    tenant_type: TenantType,
    **kwargs,
) -> Tenant:
    """Create a new tenant."""
    import uuid

    # Get next ID for this tenant scope
    result = await db.execute(
        select(Tenant.id)
        .where(and_(Tenant.account_id == account_id, Tenant.company_id == company_id))
        .order_by(Tenant.id.desc())
        .limit(1)
    )
    max_id = result.scalar_one_or_none()
    next_id = (max_id or 0) + 1

    tenant = Tenant(
        account_id=account_id,
        company_id=company_id,
        id=next_id,
        uuid=str(uuid.uuid4()),
        tenant_code=tenant_code,
        tenant_type=tenant_type,
        kyc_status=KYCStatus.PENDING,
        status=TenantStatus.ACTIVE,
        **kwargs,
    )
    db.add(tenant)
    await db.flush()
    return tenant


async def update_tenant(db: AsyncSession, tenant: Tenant, **kwargs) -> Tenant:
    """Update a tenant."""
    for key, value in kwargs.items():
        if value is not None and hasattr(tenant, key):
            setattr(tenant, key, value)
    await db.flush()
    return tenant


async def update_tenant_kyc_status(
    db: AsyncSession,
    tenant: Tenant,
    kyc_status: KYCStatus,
    verified_by_id: int | None = None,
) -> Tenant:
    """Update tenant KYC status."""
    tenant.kyc_status = kyc_status
    if kyc_status == KYCStatus.VERIFIED:
        tenant.kyc_verified_at = datetime.now(timezone.utc)
        tenant.kyc_verified_by_id = verified_by_id
    elif kyc_status in [KYCStatus.PENDING, KYCStatus.IN_PROGRESS]:
        tenant.kyc_verified_at = None
        tenant.kyc_verified_by_id = None
    await db.flush()
    return tenant


async def delete_tenant(db: AsyncSession, tenant: Tenant) -> None:
    """Delete a tenant (will cascade to contacts and documents)."""
    await db.delete(tenant)
    await db.flush()


# ----- Tenant Contact CRUD -----


async def get_contact_by_id(
    db: AsyncSession,
    contact_id: int,
    account_id: int,
    company_id: int,
) -> TenantContact | None:
    """Get a tenant contact by ID."""
    result = await db.execute(
        select(TenantContact).where(
            and_(
                TenantContact.id == contact_id,
                TenantContact.account_id == account_id,
                TenantContact.company_id == company_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_contacts_by_tenant(
    db: AsyncSession,
    tenant_id: int,
    account_id: int,
    company_id: int,
) -> list[TenantContact]:
    """Get all contacts for a tenant."""
    result = await db.execute(
        select(TenantContact)
        .where(
            and_(
                TenantContact.tenant_id == tenant_id,
                TenantContact.account_id == account_id,
                TenantContact.company_id == company_id,
            )
        )
        .order_by(TenantContact.is_primary.desc(), TenantContact.contact_name)
    )
    return list(result.scalars().all())


async def create_contact(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    tenant_id: int,
    contact_name: str,
    **kwargs,
) -> TenantContact:
    """Create a new tenant contact."""
    import uuid

    # Get next ID for this tenant scope
    result = await db.execute(
        select(TenantContact.id)
        .where(
            and_(
                TenantContact.account_id == account_id,
                TenantContact.company_id == company_id,
            )
        )
        .order_by(TenantContact.id.desc())
        .limit(1)
    )
    max_id = result.scalar_one_or_none()
    next_id = (max_id or 0) + 1

    contact = TenantContact(
        account_id=account_id,
        company_id=company_id,
        id=next_id,
        uuid=str(uuid.uuid4()),
        tenant_id=tenant_id,
        contact_name=contact_name,
        **kwargs,
    )
    db.add(contact)
    await db.flush()
    return contact


async def update_contact(
    db: AsyncSession, contact: TenantContact, **kwargs
) -> TenantContact:
    """Update a tenant contact."""
    for key, value in kwargs.items():
        if value is not None and hasattr(contact, key):
            setattr(contact, key, value)
    await db.flush()
    return contact


async def delete_contact(db: AsyncSession, contact: TenantContact) -> None:
    """Delete a tenant contact."""
    await db.delete(contact)
    await db.flush()


async def clear_primary_contacts(
    db: AsyncSession,
    tenant_id: int,
    account_id: int,
    company_id: int,
) -> None:
    """Clear primary flag from all contacts of a tenant."""
    contacts = await get_contacts_by_tenant(db, tenant_id, account_id, company_id)
    for contact in contacts:
        if contact.is_primary:
            contact.is_primary = False
    await db.flush()


# ----- Tenant Document CRUD -----


async def get_document_by_id(
    db: AsyncSession,
    document_id: int,
    account_id: int,
    company_id: int,
) -> TenantDocument | None:
    """Get a tenant document by ID."""
    result = await db.execute(
        select(TenantDocument)
        .options(selectinload(TenantDocument.document_type))
        .where(
            and_(
                TenantDocument.id == document_id,
                TenantDocument.account_id == account_id,
                TenantDocument.company_id == company_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_documents_by_tenant(
    db: AsyncSession,
    tenant_id: int,
    account_id: int,
    company_id: int,
) -> list[TenantDocument]:
    """Get all documents for a tenant."""
    result = await db.execute(
        select(TenantDocument)
        .options(selectinload(TenantDocument.document_type))
        .where(
            and_(
                TenantDocument.tenant_id == tenant_id,
                TenantDocument.account_id == account_id,
                TenantDocument.company_id == company_id,
            )
        )
        .order_by(TenantDocument.created_at.desc())
    )
    return list(result.scalars().all())


async def create_document(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    tenant_id: int,
    document_type_id: int,
    **kwargs,
) -> TenantDocument:
    """Create a new tenant document."""
    import uuid

    # Get next ID for this tenant scope
    result = await db.execute(
        select(TenantDocument.id)
        .where(
            and_(
                TenantDocument.account_id == account_id,
                TenantDocument.company_id == company_id,
            )
        )
        .order_by(TenantDocument.id.desc())
        .limit(1)
    )
    max_id = result.scalar_one_or_none()
    next_id = (max_id or 0) + 1

    document = TenantDocument(
        account_id=account_id,
        company_id=company_id,
        id=next_id,
        uuid=str(uuid.uuid4()),
        tenant_id=tenant_id,
        document_type_id=document_type_id,
        verification_status=DocumentVerificationStatus.PENDING,
        **kwargs,
    )
    db.add(document)
    await db.flush()
    return document


async def update_document(
    db: AsyncSession, document: TenantDocument, **kwargs
) -> TenantDocument:
    """Update a tenant document."""
    for key, value in kwargs.items():
        if value is not None and hasattr(document, key):
            setattr(document, key, value)
    await db.flush()
    return document


async def verify_document(
    db: AsyncSession,
    document: TenantDocument,
    verified_by_id: int,
) -> TenantDocument:
    """Verify a tenant document."""
    document.verification_status = DocumentVerificationStatus.VERIFIED
    document.verified_at = datetime.now(timezone.utc)
    document.verified_by_id = verified_by_id
    document.rejection_reason = None
    await db.flush()
    return document


async def reject_document(
    db: AsyncSession,
    document: TenantDocument,
    reason: str,
    rejected_by_id: int,
) -> TenantDocument:
    """Reject a tenant document."""
    document.verification_status = DocumentVerificationStatus.REJECTED
    document.verified_at = datetime.now(timezone.utc)
    document.verified_by_id = rejected_by_id
    document.rejection_reason = reason
    await db.flush()
    return document


async def delete_document(db: AsyncSession, document: TenantDocument) -> None:
    """Delete a tenant document."""
    await db.delete(document)
    await db.flush()


async def get_expiring_documents(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    days_until_expiry: int = 30,
) -> list[TenantDocument]:
    """Get documents expiring within specified days."""
    from datetime import timedelta

    expiry_date = date.today() + timedelta(days=days_until_expiry)
    result = await db.execute(
        select(TenantDocument)
        .options(selectinload(TenantDocument.document_type))
        .where(
            and_(
                TenantDocument.account_id == account_id,
                TenantDocument.company_id == company_id,
                TenantDocument.expiry_date <= expiry_date,
                TenantDocument.expiry_date >= date.today(),
                TenantDocument.verification_status
                == DocumentVerificationStatus.VERIFIED,
            )
        )
        .order_by(TenantDocument.expiry_date)
    )
    return list(result.scalars().all())
