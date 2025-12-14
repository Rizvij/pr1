"""Tenant management business logic services."""

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions import NotFoundError, ValidationError
from . import crud
from .models import (
    DocumentVerificationStatus,
    KYCStatus,
    Tenant,
    TenantDocument,
    TenantType,
)
from .schemas import (
    TenantContactCreate,
    TenantContactUpdate,
    TenantDocumentCreate,
    TenantDocumentUpdate,
    TenantEntityCreate,
    TenantIndividualCreate,
    TenantUpdate,
)

# ----- Tenant Services -----


async def create_individual_tenant(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    data: TenantIndividualCreate,
) -> Tenant:
    """Create a new individual tenant."""
    # Check for duplicate tenant code
    existing = await crud.get_tenant_by_code(
        db, data.tenant_code, account_id, company_id
    )
    if existing:
        raise ValidationError(f"Tenant with code '{data.tenant_code}' already exists")

    tenant = await crud.create_tenant(
        db=db,
        account_id=account_id,
        company_id=company_id,
        tenant_code=data.tenant_code,
        tenant_type=TenantType.INDIVIDUAL,
        first_name=data.first_name,
        last_name=data.last_name,
        date_of_birth=data.date_of_birth,
        nationality=data.nationality,
        passport_number=data.passport_number,
        emirates_id=data.emirates_id,
        email=data.email,
        phone=data.phone,
        mobile=data.mobile,
        address=data.address,
        city=data.city,
        country=data.country,
        notes=data.notes,
    )

    await db.commit()
    return tenant


async def create_entity_tenant(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    data: TenantEntityCreate,
) -> Tenant:
    """Create a new entity tenant."""
    # Check for duplicate tenant code
    existing = await crud.get_tenant_by_code(
        db, data.tenant_code, account_id, company_id
    )
    if existing:
        raise ValidationError(f"Tenant with code '{data.tenant_code}' already exists")

    tenant = await crud.create_tenant(
        db=db,
        account_id=account_id,
        company_id=company_id,
        tenant_code=data.tenant_code,
        tenant_type=TenantType.ENTITY,
        entity_name=data.entity_name,
        trade_license_number=data.trade_license_number,
        registration_number=data.registration_number,
        email=data.email,
        phone=data.phone,
        mobile=data.mobile,
        address=data.address,
        city=data.city,
        country=data.country,
        notes=data.notes,
    )

    await db.commit()
    return tenant


async def update_tenant(
    db: AsyncSession,
    tenant_id: int,
    account_id: int,
    company_id: int,
    data: TenantUpdate,
) -> Tenant:
    """Update a tenant."""
    tenant = await crud.get_tenant_by_id(db, tenant_id, account_id, company_id)
    if not tenant:
        raise NotFoundError(f"Tenant with ID {tenant_id} not found")

    # Check for duplicate code if changing
    if data.tenant_code and data.tenant_code != tenant.tenant_code:
        existing = await crud.get_tenant_by_code(
            db, data.tenant_code, account_id, company_id
        )
        if existing:
            raise ValidationError(
                f"Tenant with code '{data.tenant_code}' already exists"
            )

    updated = await crud.update_tenant(
        db, tenant, **data.model_dump(exclude_unset=True)
    )

    await db.commit()
    return updated


async def delete_tenant(
    db: AsyncSession,
    tenant_id: int,
    account_id: int,
    company_id: int,
) -> None:
    """Delete a tenant."""
    tenant = await crud.get_tenant_by_id(db, tenant_id, account_id, company_id)
    if not tenant:
        raise NotFoundError(f"Tenant with ID {tenant_id} not found")

    await crud.delete_tenant(db, tenant)
    await db.commit()


async def update_kyc_status(
    db: AsyncSession,
    tenant_id: int,
    account_id: int,
    company_id: int,
    kyc_status: KYCStatus,
    updated_by_id: int,
) -> Tenant:
    """Update tenant KYC status."""
    tenant = await crud.get_tenant_by_id(db, tenant_id, account_id, company_id)
    if not tenant:
        raise NotFoundError(f"Tenant with ID {tenant_id} not found")

    updated = await crud.update_tenant_kyc_status(db, tenant, kyc_status, updated_by_id)

    await db.commit()
    return updated


async def derive_kyc_status(
    db: AsyncSession,
    tenant_id: int,
    account_id: int,
    company_id: int,
) -> KYCStatus:
    """Derive KYC status based on document verification status.

    Rules:
    - All mandatory docs verified + not expired = VERIFIED
    - Any mandatory doc rejected = REJECTED
    - Any doc expired = EXPIRED
    - Documents being processed = IN_PROGRESS
    - No docs or all pending = PENDING
    """
    tenant = await crud.get_tenant_by_id(
        db, tenant_id, account_id, company_id, include_details=True
    )
    if not tenant:
        raise NotFoundError(f"Tenant with ID {tenant_id} not found")

    # Get mandatory document types for this tenant type
    doc_types = await crud.get_all_document_types(
        db, is_active=True, applicable_to=tenant.tenant_type
    )
    mandatory_types = {dt.id for dt in doc_types if dt.is_mandatory}

    if not tenant.documents:
        return KYCStatus.PENDING

    # Group documents by type
    docs_by_type: dict[int, list[TenantDocument]] = {}
    for doc in tenant.documents:
        if doc.document_type_id not in docs_by_type:
            docs_by_type[doc.document_type_id] = []
        docs_by_type[doc.document_type_id].append(doc)

    # Check each mandatory type
    all_verified = True
    has_rejected = False
    has_expired = False
    has_pending_or_in_progress = False

    for type_id in mandatory_types:
        type_docs = docs_by_type.get(type_id, [])
        if not type_docs:
            all_verified = False
            has_pending_or_in_progress = True
            continue

        # Get latest doc of this type
        latest_doc = max(type_docs, key=lambda d: d.created_at)

        if latest_doc.verification_status == DocumentVerificationStatus.REJECTED:
            has_rejected = True
        elif latest_doc.verification_status == DocumentVerificationStatus.PENDING:
            all_verified = False
            has_pending_or_in_progress = True
        elif latest_doc.verification_status == DocumentVerificationStatus.VERIFIED:
            if latest_doc.is_expired:
                has_expired = True
                all_verified = False
        elif latest_doc.verification_status == DocumentVerificationStatus.EXPIRED:
            has_expired = True
            all_verified = False

    if has_rejected:
        return KYCStatus.REJECTED
    if has_expired:
        return KYCStatus.EXPIRED
    if all_verified and mandatory_types:
        return KYCStatus.VERIFIED
    if has_pending_or_in_progress:
        return KYCStatus.IN_PROGRESS

    return KYCStatus.PENDING


# ----- Contact Services -----


async def add_contact(
    db: AsyncSession,
    tenant_id: int,
    account_id: int,
    company_id: int,
    data: TenantContactCreate,
) -> Tenant:
    """Add a contact to a tenant."""
    tenant = await crud.get_tenant_by_id(db, tenant_id, account_id, company_id)
    if not tenant:
        raise NotFoundError(f"Tenant with ID {tenant_id} not found")

    # If marking as primary, clear other primaries
    if data.is_primary:
        await crud.clear_primary_contacts(db, tenant_id, account_id, company_id)

    await crud.create_contact(
        db=db,
        account_id=account_id,
        company_id=company_id,
        tenant_id=tenant_id,
        **data.model_dump(),
    )

    await db.commit()
    return await crud.get_tenant_by_id(
        db, tenant_id, account_id, company_id, include_details=True
    )


async def update_contact(
    db: AsyncSession,
    tenant_id: int,
    contact_id: int,
    account_id: int,
    company_id: int,
    data: TenantContactUpdate,
) -> Tenant:
    """Update a tenant contact."""
    contact = await crud.get_contact_by_id(db, contact_id, account_id, company_id)
    if not contact or contact.tenant_id != tenant_id:
        raise NotFoundError(f"Contact with ID {contact_id} not found for this tenant")

    # If marking as primary, clear other primaries
    if data.is_primary:
        await crud.clear_primary_contacts(db, tenant_id, account_id, company_id)

    await crud.update_contact(db, contact, **data.model_dump(exclude_unset=True))

    await db.commit()
    return await crud.get_tenant_by_id(
        db, tenant_id, account_id, company_id, include_details=True
    )


async def remove_contact(
    db: AsyncSession,
    tenant_id: int,
    contact_id: int,
    account_id: int,
    company_id: int,
) -> Tenant:
    """Remove a contact from a tenant."""
    contact = await crud.get_contact_by_id(db, contact_id, account_id, company_id)
    if not contact or contact.tenant_id != tenant_id:
        raise NotFoundError(f"Contact with ID {contact_id} not found for this tenant")

    await crud.delete_contact(db, contact)

    await db.commit()
    return await crud.get_tenant_by_id(
        db, tenant_id, account_id, company_id, include_details=True
    )


# ----- Document Services -----


async def add_document(
    db: AsyncSession,
    tenant_id: int,
    account_id: int,
    company_id: int,
    data: TenantDocumentCreate,
) -> Tenant:
    """Add a document to a tenant."""
    tenant = await crud.get_tenant_by_id(db, tenant_id, account_id, company_id)
    if not tenant:
        raise NotFoundError(f"Tenant with ID {tenant_id} not found")

    # Verify document type exists
    doc_type = await crud.get_document_type_by_id(db, data.document_type_id)
    if not doc_type:
        raise NotFoundError(f"Document type with ID {data.document_type_id} not found")

    # Check if document type is applicable to tenant type
    if doc_type.applicable_to and doc_type.applicable_to != tenant.tenant_type:
        raise ValidationError(
            f"Document type '{doc_type.name}' is not applicable to "
            f"{tenant.tenant_type.value} tenants"
        )

    await crud.create_document(
        db=db,
        account_id=account_id,
        company_id=company_id,
        tenant_id=tenant_id,
        **data.model_dump(),
    )

    await db.commit()
    return await crud.get_tenant_by_id(
        db, tenant_id, account_id, company_id, include_details=True
    )


async def update_document(
    db: AsyncSession,
    tenant_id: int,
    document_id: int,
    account_id: int,
    company_id: int,
    data: TenantDocumentUpdate,
) -> Tenant:
    """Update a tenant document."""
    document = await crud.get_document_by_id(db, document_id, account_id, company_id)
    if not document or document.tenant_id != tenant_id:
        raise NotFoundError(f"Document with ID {document_id} not found for this tenant")

    await crud.update_document(db, document, **data.model_dump(exclude_unset=True))

    await db.commit()
    return await crud.get_tenant_by_id(
        db, tenant_id, account_id, company_id, include_details=True
    )


async def verify_document(
    db: AsyncSession,
    tenant_id: int,
    document_id: int,
    account_id: int,
    company_id: int,
    verified_by_id: int,
) -> Tenant:
    """Verify a tenant document."""
    document = await crud.get_document_by_id(db, document_id, account_id, company_id)
    if not document or document.tenant_id != tenant_id:
        raise NotFoundError(f"Document with ID {document_id} not found for this tenant")

    if document.verification_status != DocumentVerificationStatus.PENDING:
        raise ValidationError(
            f"Cannot verify document in '{document.verification_status.value}' status"
        )

    await crud.verify_document(db, document, verified_by_id)

    # Derive and update KYC status
    new_kyc_status = await derive_kyc_status(db, tenant_id, account_id, company_id)
    tenant = await crud.get_tenant_by_id(db, tenant_id, account_id, company_id)
    if tenant and tenant.kyc_status != new_kyc_status:
        await crud.update_tenant_kyc_status(db, tenant, new_kyc_status, verified_by_id)

    await db.commit()
    return await crud.get_tenant_by_id(
        db, tenant_id, account_id, company_id, include_details=True
    )


async def reject_document(
    db: AsyncSession,
    tenant_id: int,
    document_id: int,
    account_id: int,
    company_id: int,
    reason: str,
    rejected_by_id: int,
) -> Tenant:
    """Reject a tenant document."""
    document = await crud.get_document_by_id(db, document_id, account_id, company_id)
    if not document or document.tenant_id != tenant_id:
        raise NotFoundError(f"Document with ID {document_id} not found for this tenant")

    if document.verification_status != DocumentVerificationStatus.PENDING:
        raise ValidationError(
            f"Cannot reject document in '{document.verification_status.value}' status"
        )

    await crud.reject_document(db, document, reason, rejected_by_id)

    # Derive and update KYC status
    new_kyc_status = await derive_kyc_status(db, tenant_id, account_id, company_id)
    tenant = await crud.get_tenant_by_id(db, tenant_id, account_id, company_id)
    if tenant and tenant.kyc_status != new_kyc_status:
        await crud.update_tenant_kyc_status(db, tenant, new_kyc_status, rejected_by_id)

    await db.commit()
    return await crud.get_tenant_by_id(
        db, tenant_id, account_id, company_id, include_details=True
    )


async def remove_document(
    db: AsyncSession,
    tenant_id: int,
    document_id: int,
    account_id: int,
    company_id: int,
) -> Tenant:
    """Remove a document from a tenant."""
    document = await crud.get_document_by_id(db, document_id, account_id, company_id)
    if not document or document.tenant_id != tenant_id:
        raise NotFoundError(f"Document with ID {document_id} not found for this tenant")

    await crud.delete_document(db, document)

    await db.commit()
    return await crud.get_tenant_by_id(
        db, tenant_id, account_id, company_id, include_details=True
    )
