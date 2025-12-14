"""Vendor management API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ..auth.dependencies import CurrentUser
from ..commons import BaseResponse, PaginatedResponse
from . import crud, services
from .models import LeaseStatus, VendorStatus, VendorType
from .schemas import (
    LeaseTerminateRequest,
    VendorCreate,
    VendorLeaseCoverageCreate,
    VendorLeaseCreate,
    VendorLeaseResponse,
    VendorLeaseTermCreate,
    VendorLeaseUpdate,
    VendorLeaseWithDetails,
    VendorResponse,
    VendorUpdate,
)

router = APIRouter(prefix="/vendors", tags=["Vendors"])
leases_router = APIRouter(prefix="/vendor-leases", tags=["Vendor Leases"])


# ----- Vendors -----


@router.get("", response_model=BaseResponse[PaginatedResponse[VendorResponse]])
async def list_vendors(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: VendorStatus | None = Query(None),
    vendor_type: VendorType | None = Query(None),
    search: str | None = Query(None),
):
    """Get vendors with pagination and filtering."""
    skip = (page - 1) * page_size
    vendors, total = await crud.get_vendors(
        db=db,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        skip=skip,
        limit=page_size,
        status=status,
        vendor_type=vendor_type,
        search=search,
    )

    return BaseResponse(
        success=True,
        data=PaginatedResponse.from_items(
            items=[VendorResponse.model_validate(v) for v in vendors],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@router.get("/{vendor_id}", response_model=BaseResponse[VendorResponse])
async def get_vendor(
    vendor_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a vendor by ID."""
    vendor = await crud.get_vendor_by_id(
        db, vendor_id, current_user.account_id, current_user.company_id
    )
    if not vendor:
        from ...core.exceptions import NotFoundError

        raise NotFoundError(f"Vendor with ID {vendor_id} not found")

    return BaseResponse(
        success=True,
        data=VendorResponse.model_validate(vendor),
    )


@router.post("", response_model=BaseResponse[VendorResponse])
async def create_vendor(
    data: VendorCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new vendor."""
    vendor = await services.create_vendor(
        db=db,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Vendor created successfully",
        data=VendorResponse.model_validate(vendor),
    )


@router.put("/{vendor_id}", response_model=BaseResponse[VendorResponse])
async def update_vendor(
    vendor_id: int,
    data: VendorUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a vendor."""
    vendor = await services.update_vendor(
        db=db,
        vendor_id=vendor_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Vendor updated successfully",
        data=VendorResponse.model_validate(vendor),
    )


@router.delete("/{vendor_id}", response_model=BaseResponse[None])
async def delete_vendor(
    vendor_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a vendor."""
    await services.delete_vendor(
        db=db,
        vendor_id=vendor_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
    )

    return BaseResponse(
        success=True,
        message="Vendor deleted successfully",
    )


# ----- Vendor Leases -----


@leases_router.get(
    "", response_model=BaseResponse[PaginatedResponse[VendorLeaseResponse]]
)
async def list_leases(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vendor_id: int | None = Query(None),
    status: LeaseStatus | None = Query(None),
    search: str | None = Query(None),
):
    """Get vendor leases with pagination and filtering."""
    skip = (page - 1) * page_size
    leases, total = await crud.get_leases(
        db=db,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        skip=skip,
        limit=page_size,
        vendor_id=vendor_id,
        status=status,
        search=search,
    )

    return BaseResponse(
        success=True,
        data=PaginatedResponse.from_items(
            items=[VendorLeaseResponse.model_validate(lease) for lease in leases],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@leases_router.get("/{lease_id}", response_model=BaseResponse[VendorLeaseWithDetails])
async def get_lease(
    lease_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a vendor lease by ID with full details."""
    lease = await crud.get_lease_by_id(
        db,
        lease_id,
        current_user.account_id,
        current_user.company_id,
        include_details=True,
    )
    if not lease:
        from ...core.exceptions import NotFoundError

        raise NotFoundError(f"Lease with ID {lease_id} not found")

    return BaseResponse(
        success=True,
        data=VendorLeaseWithDetails.model_validate(lease),
    )


@leases_router.post("", response_model=BaseResponse[VendorLeaseResponse])
async def create_lease(
    data: VendorLeaseCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new vendor lease."""
    lease = await services.create_lease(
        db=db,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Vendor lease created successfully",
        data=VendorLeaseResponse.model_validate(lease),
    )


@leases_router.put("/{lease_id}", response_model=BaseResponse[VendorLeaseResponse])
async def update_lease(
    lease_id: int,
    data: VendorLeaseUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a vendor lease (only DRAFT status)."""
    lease = await services.update_lease(
        db=db,
        lease_id=lease_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Vendor lease updated successfully",
        data=VendorLeaseResponse.model_validate(lease),
    )


@leases_router.post(
    "/{lease_id}/activate", response_model=BaseResponse[VendorLeaseResponse]
)
async def activate_lease(
    lease_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Activate a vendor lease."""
    lease = await services.activate_lease(
        db=db,
        lease_id=lease_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
    )

    return BaseResponse(
        success=True,
        message="Vendor lease activated successfully",
        data=VendorLeaseResponse.model_validate(lease),
    )


@leases_router.post(
    "/{lease_id}/terminate", response_model=BaseResponse[VendorLeaseResponse]
)
async def terminate_lease(
    lease_id: int,
    data: LeaseTerminateRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Terminate a vendor lease."""
    lease = await services.terminate_lease(
        db=db,
        lease_id=lease_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        reason=data.reason,
    )

    return BaseResponse(
        success=True,
        message="Vendor lease terminated successfully",
        data=VendorLeaseResponse.model_validate(lease),
    )


@leases_router.delete("/{lease_id}", response_model=BaseResponse[None])
async def delete_lease(
    lease_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a vendor lease (only DRAFT or TERMINATED status)."""
    await services.delete_lease(
        db=db,
        lease_id=lease_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
    )

    return BaseResponse(
        success=True,
        message="Vendor lease deleted successfully",
    )


# ----- Lease Terms -----


@leases_router.post(
    "/{lease_id}/terms",
    response_model=BaseResponse[VendorLeaseWithDetails],
)
async def add_lease_term(
    lease_id: int,
    data: VendorLeaseTermCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add a new term to a lease (for renewals/adjustments)."""
    lease = await services.add_lease_term(
        db=db,
        lease_id=lease_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Lease term added successfully",
        data=VendorLeaseWithDetails.model_validate(lease),
    )


# ----- Lease Coverage -----


@leases_router.post(
    "/{lease_id}/coverage",
    response_model=BaseResponse[VendorLeaseWithDetails],
)
async def add_lease_coverage(
    lease_id: int,
    data: VendorLeaseCoverageCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add coverage to a lease."""
    lease = await services.add_lease_coverage(
        db=db,
        lease_id=lease_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        data=data,
    )

    return BaseResponse(
        success=True,
        message="Lease coverage added successfully",
        data=VendorLeaseWithDetails.model_validate(lease),
    )


@leases_router.delete(
    "/{lease_id}/coverage/{coverage_id}",
    response_model=BaseResponse[VendorLeaseWithDetails],
)
async def remove_lease_coverage(
    lease_id: int,
    coverage_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove coverage from a lease (only DRAFT status)."""
    lease = await services.remove_lease_coverage(
        db=db,
        lease_id=lease_id,
        coverage_id=coverage_id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
    )

    return BaseResponse(
        success=True,
        message="Lease coverage removed successfully",
        data=VendorLeaseWithDetails.model_validate(lease),
    )
