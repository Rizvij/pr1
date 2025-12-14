"""Tenant management API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ..auth.dependencies import CurrentUser
from ..commons import BaseResponse, PaginatedResponse
from . import crud, services
from .models import KYCStatus, TenantStatus, TenantType
from .schemas import (
    DocumentRejectRequest,
    DocumentTypeCreate,
    DocumentTypeResponse,
    KYCUpdateRequest,
    TenantContactCreate,
    TenantContactUpdate,
    TenantDocumentCreate,
    TenantDocumentUpdate,
    TenantEntityCreate,
    TenantIndividualCreate,
    TenantResponse,
    TenantUpdate,
    TenantWithDetails,
)

router = APIRouter(prefix="/tenants", tags=["Tenants"])
doc_types_router = APIRouter(prefix="/document-types", tags=["Document Types"])


# ----- Document Types -----


@doc_types_router.get("", response_model=BaseResponse[list[DocumentTypeResponse]])
async def list_document_types(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    is_active: bool | None = Query(None),
    applicable_to: TenantType | None = Query(None),
):
    """Get all document types."""
    doc_types = await crud.get_all_document_types(
        db, is_active=is_active, applicable_to=applicable_to
    )
    return BaseResponse(
        success=True,
        data=[DocumentTypeResponse.model_validate(dt) for dt in doc_types],
    )


@doc_types_router.post("", response_model=BaseResponse[DocumentTypeResponse])
async def create_document_type(
    data: DocumentTypeCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new document type (admin only)."""
    # Check for duplicate code
    existing = await crud.get_document_type_by_code(db, data.code.upper())
    if existing:
        from ...core.exceptions import ValidationError

        raise ValidationError(f"Document type with code '{data.code}' already exists")

    doc_type = await crud.create_document_type(
        db,
        code=data.code,
        name=data.name,
        description=data.description,
        applicable_to=data.applicable_to,
        is_mandatory=data.is_mandatory,
    )
    await db.commit()

    return BaseResponse(
        success=True,
        message="Document type created successfully",
        data=DocumentTypeResponse.model_validate(doc_type),
    )


# ----- Tenants -----


@router.get("", response_model=BaseResponse[PaginatedResponse[TenantResponse]])
async def list_tenants(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_type: TenantType | None = Query(None),
    status: TenantStatus | None = Query(None),
    kyc_status: KYCStatus | None = Query(None),
    search: str | None = Query(None),
):
    """Get tenants with pagination and filtering."""
    skip = (page - 1) * page_size
    tenants, total = await crud.get_tenants(
        db=db,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        skip=skip,
        limit=page_size,
        tenant_type=tenant_type,
        status=status,
        kyc_status=kyc_status,
        search=search,
    )

    return BaseResponse(
        success=True,
        data=PaginatedResponse.from_items(
            items=[TenantResponse.model_validate(t) for t in tenants],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@router.get("/{tenant_id}", response_model=BaseResponse[TenantWithDetails])
async def get_tenant(
    tenant_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a tenant by ID with full details."""
    tenant = await crud.get_tenant_by_id(
        db,
        tenant_id,
        current_user.account_id,
        current_user.company_id,
        include_details=True,
    )
    if not tenant:
        from ...core.exceptions import NotFoundError

        raise NotFoundError(f"Tenant with ID {tenant_id} not found")

    return BaseResponse(
        success=True,
        data=TenantWithDetails.model_validate(tenant),
    )


@router.post("/individual", response_model=BaseResponse[TenantResponse])
async def create_individual_tenant(
    data: TenantIndividualCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new individual tenant."""
    tenant = await services.create_individual_tenant(
        db=db,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Individual tenant created successfully",
        data=TenantResponse.model_validate(tenant),
    )


@router.post("/entity", response_model=BaseResponse[TenantResponse])
async def create_entity_tenant(
    data: TenantEntityCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new entity tenant."""
    tenant = await services.create_entity_tenant(
        db=db,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Entity tenant created successfully",
        data=TenantResponse.model_validate(tenant),
    )


@router.put("/{tenant_id}", response_model=BaseResponse[TenantResponse])
async def update_tenant(
    tenant_id: int,
    data: TenantUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a tenant."""
    tenant = await services.update_tenant(
        db=db,
        tenant_id=tenant_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Tenant updated successfully",
        data=TenantResponse.model_validate(tenant),
    )


@router.delete("/{tenant_id}", response_model=BaseResponse[None])
async def delete_tenant(
    tenant_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a tenant."""
    await services.delete_tenant(
        db=db,
        tenant_id=tenant_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
    )

    return BaseResponse(
        success=True,
        message="Tenant deleted successfully",
    )


@router.put("/{tenant_id}/kyc-status", response_model=BaseResponse[TenantResponse])
async def update_kyc_status(
    tenant_id: int,
    data: KYCUpdateRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Manually update tenant KYC status."""
    tenant = await services.update_kyc_status(
        db=db,
        tenant_id=tenant_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        kyc_status=data.kyc_status,
        updated_by_id=current_user.id,
    )

    return BaseResponse(
        success=True,
        message=f"KYC status updated to {data.kyc_status.value}",
        data=TenantResponse.model_validate(tenant),
    )


# ----- Tenant Contacts -----


@router.post("/{tenant_id}/contacts", response_model=BaseResponse[TenantWithDetails])
async def add_contact(
    tenant_id: int,
    data: TenantContactCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add a contact to a tenant."""
    tenant = await services.add_contact(
        db=db,
        tenant_id=tenant_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Contact added successfully",
        data=TenantWithDetails.model_validate(tenant),
    )


@router.put(
    "/{tenant_id}/contacts/{contact_id}",
    response_model=BaseResponse[TenantWithDetails],
)
async def update_contact(
    tenant_id: int,
    contact_id: int,
    data: TenantContactUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a tenant contact."""
    tenant = await services.update_contact(
        db=db,
        tenant_id=tenant_id,
        contact_id=contact_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Contact updated successfully",
        data=TenantWithDetails.model_validate(tenant),
    )


@router.delete(
    "/{tenant_id}/contacts/{contact_id}",
    response_model=BaseResponse[TenantWithDetails],
)
async def remove_contact(
    tenant_id: int,
    contact_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove a contact from a tenant."""
    tenant = await services.remove_contact(
        db=db,
        tenant_id=tenant_id,
        contact_id=contact_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
    )

    return BaseResponse(
        success=True,
        message="Contact removed successfully",
        data=TenantWithDetails.model_validate(tenant),
    )


# ----- Tenant Documents -----


@router.post("/{tenant_id}/documents", response_model=BaseResponse[TenantWithDetails])
async def add_document(
    tenant_id: int,
    data: TenantDocumentCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add a document to a tenant."""
    tenant = await services.add_document(
        db=db,
        tenant_id=tenant_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Document added successfully",
        data=TenantWithDetails.model_validate(tenant),
    )


@router.put(
    "/{tenant_id}/documents/{document_id}",
    response_model=BaseResponse[TenantWithDetails],
)
async def update_document(
    tenant_id: int,
    document_id: int,
    data: TenantDocumentUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a tenant document."""
    tenant = await services.update_document(
        db=db,
        tenant_id=tenant_id,
        document_id=document_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Document updated successfully",
        data=TenantWithDetails.model_validate(tenant),
    )


@router.post(
    "/{tenant_id}/documents/{document_id}/verify",
    response_model=BaseResponse[TenantWithDetails],
)
async def verify_document(
    tenant_id: int,
    document_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Verify a tenant document."""
    tenant = await services.verify_document(
        db=db,
        tenant_id=tenant_id,
        document_id=document_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        verified_by_id=current_user.id,
    )

    return BaseResponse(
        success=True,
        message="Document verified successfully",
        data=TenantWithDetails.model_validate(tenant),
    )


@router.post(
    "/{tenant_id}/documents/{document_id}/reject",
    response_model=BaseResponse[TenantWithDetails],
)
async def reject_document(
    tenant_id: int,
    document_id: int,
    data: DocumentRejectRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reject a tenant document."""
    tenant = await services.reject_document(
        db=db,
        tenant_id=tenant_id,
        document_id=document_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        reason=data.reason,
        rejected_by_id=current_user.id,
    )

    return BaseResponse(
        success=True,
        message="Document rejected",
        data=TenantWithDetails.model_validate(tenant),
    )


@router.delete(
    "/{tenant_id}/documents/{document_id}",
    response_model=BaseResponse[TenantWithDetails],
)
async def remove_document(
    tenant_id: int,
    document_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove a document from a tenant."""
    tenant = await services.remove_document(
        db=db,
        tenant_id=tenant_id,
        document_id=document_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
    )

    return BaseResponse(
        success=True,
        message="Document removed successfully",
        data=TenantWithDetails.model_validate(tenant),
    )


# ----- Expiring Documents -----


@router.get("/reports/expiring-documents", response_model=BaseResponse[list])
async def get_expiring_documents(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=365),
):
    """Get documents expiring within specified days."""
    from .schemas import TenantDocumentResponse

    documents = await crud.get_expiring_documents(
        db=db,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        days_until_expiry=days,
    )

    return BaseResponse(
        success=True,
        data=[TenantDocumentResponse.model_validate(d) for d in documents],
    )
