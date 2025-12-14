"""Vendor management business logic services."""

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions import NotFoundError, ValidationError
from ..property_management import crud as property_crud
from . import crud
from .models import CoverageScope, LeaseStatus, Vendor, VendorLease
from .schemas import (
    VendorCreate,
    VendorLeaseCoverageCreate,
    VendorLeaseCreate,
    VendorLeaseTermCreate,
    VendorLeaseUpdate,
    VendorUpdate,
)

# ----- Vendor Services -----


async def create_vendor(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    data: VendorCreate,
) -> Vendor:
    """Create a new vendor with validation."""
    # Check for duplicate vendor code
    existing = await crud.get_vendor_by_code(
        db, data.vendor_code, account_id, company_id
    )
    if existing:
        raise ValidationError(f"Vendor with code '{data.vendor_code}' already exists")

    vendor = await crud.create_vendor(
        db=db,
        account_id=account_id,
        company_id=company_id,
        **data.model_dump(),
    )

    await db.commit()
    return vendor


async def update_vendor(
    db: AsyncSession,
    vendor_id: int,
    account_id: int,
    company_id: int,
    data: VendorUpdate,
) -> Vendor:
    """Update a vendor."""
    vendor = await crud.get_vendor_by_id(db, vendor_id, account_id, company_id)
    if not vendor:
        raise NotFoundError(f"Vendor with ID {vendor_id} not found")

    # Check for duplicate code if changing
    if data.vendor_code and data.vendor_code != vendor.vendor_code:
        existing = await crud.get_vendor_by_code(
            db, data.vendor_code, account_id, company_id
        )
        if existing:
            raise ValidationError(
                f"Vendor with code '{data.vendor_code}' already exists"
            )

    updated = await crud.update_vendor(
        db, vendor, **data.model_dump(exclude_unset=True)
    )

    await db.commit()
    return updated


async def delete_vendor(
    db: AsyncSession,
    vendor_id: int,
    account_id: int,
    company_id: int,
) -> None:
    """Delete a vendor."""
    vendor = await crud.get_vendor_by_id(db, vendor_id, account_id, company_id)
    if not vendor:
        raise NotFoundError(f"Vendor with ID {vendor_id} not found")

    await crud.delete_vendor(db, vendor)
    await db.commit()


# ----- Vendor Lease Services -----


async def create_lease(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    data: VendorLeaseCreate,
) -> VendorLease:
    """Create a new vendor lease with validation."""
    # Verify vendor exists
    vendor = await crud.get_vendor_by_id(db, data.vendor_id, account_id, company_id)
    if not vendor:
        raise NotFoundError(f"Vendor with ID {data.vendor_id} not found")

    # Check for duplicate lease code
    existing = await crud.get_lease_by_code(db, data.lease_code, account_id, company_id)
    if existing:
        raise ValidationError(f"Lease with code '{data.lease_code}' already exists")

    # Validate dates
    if data.end_date < data.start_date:
        raise ValidationError("End date must be after start date")

    lease = await crud.create_lease(
        db=db,
        account_id=account_id,
        company_id=company_id,
        vendor_id=data.vendor_id,
        lease_code=data.lease_code,
        start_date=data.start_date,
        end_date=data.end_date,
        rent_amount=data.rent_amount,
        currency=data.currency,
        billing_cycle=data.billing_cycle,
        security_deposit=data.security_deposit,
        description=data.description,
        notes=data.notes,
    )

    await db.commit()

    # Reload with vendor relationship
    return await crud.get_lease_by_id(db, lease.id, account_id, company_id)


async def update_lease(
    db: AsyncSession,
    lease_id: int,
    account_id: int,
    company_id: int,
    data: VendorLeaseUpdate,
) -> VendorLease:
    """Update a vendor lease."""
    lease = await crud.get_lease_by_id(db, lease_id, account_id, company_id)
    if not lease:
        raise NotFoundError(f"Lease with ID {lease_id} not found")

    # Only allow updates on DRAFT leases
    if lease.status != LeaseStatus.DRAFT:
        raise ValidationError(
            f"Cannot update lease in '{lease.status.value}' status. "
            "Only DRAFT leases can be updated."
        )

    # Check for duplicate code if changing
    if data.lease_code and data.lease_code != lease.lease_code:
        existing = await crud.get_lease_by_code(
            db, data.lease_code, account_id, company_id
        )
        if existing:
            raise ValidationError(f"Lease with code '{data.lease_code}' already exists")

    # Validate dates if both provided
    start = data.start_date or lease.start_date
    end = data.end_date or lease.end_date
    if end < start:
        raise ValidationError("End date must be after start date")

    updated = await crud.update_lease(db, lease, **data.model_dump(exclude_unset=True))

    await db.commit()
    return await crud.get_lease_by_id(db, updated.id, account_id, company_id)


async def activate_lease(
    db: AsyncSession,
    lease_id: int,
    account_id: int,
    company_id: int,
) -> VendorLease:
    """Activate a vendor lease."""
    lease = await crud.get_lease_by_id(
        db, lease_id, account_id, company_id, include_details=True
    )
    if not lease:
        raise NotFoundError(f"Lease with ID {lease_id} not found")

    if lease.status != LeaseStatus.DRAFT:
        raise ValidationError(
            f"Cannot activate lease in '{lease.status.value}' status. "
            "Only DRAFT leases can be activated."
        )

    # Validate that lease has at least one coverage
    if not lease.coverages:
        raise ValidationError(
            "Cannot activate lease without coverage. "
            "Add at least one property or unit coverage."
        )

    activated = await crud.activate_lease(db, lease)

    # Create initial term
    await crud.create_lease_term(
        db=db,
        account_id=account_id,
        company_id=company_id,
        lease_id=lease.id,
        term_number=1,
        start_date=lease.start_date,
        end_date=lease.end_date,
        rent_amount=lease.rent_amount,
        reason="Initial term",
    )

    await db.commit()
    return await crud.get_lease_by_id(db, activated.id, account_id, company_id)


async def terminate_lease(
    db: AsyncSession,
    lease_id: int,
    account_id: int,
    company_id: int,
    reason: str,
) -> VendorLease:
    """Terminate a vendor lease."""
    lease = await crud.get_lease_by_id(db, lease_id, account_id, company_id)
    if not lease:
        raise NotFoundError(f"Lease with ID {lease_id} not found")

    if lease.status != LeaseStatus.ACTIVE:
        raise ValidationError(
            f"Cannot terminate lease in '{lease.status.value}' status. "
            "Only ACTIVE leases can be terminated."
        )

    terminated = await crud.terminate_lease(db, lease, reason)

    await db.commit()
    return await crud.get_lease_by_id(db, terminated.id, account_id, company_id)


async def delete_lease(
    db: AsyncSession,
    lease_id: int,
    account_id: int,
    company_id: int,
) -> None:
    """Delete a vendor lease."""
    lease = await crud.get_lease_by_id(db, lease_id, account_id, company_id)
    if not lease:
        raise NotFoundError(f"Lease with ID {lease_id} not found")

    # Only allow deletion of DRAFT or TERMINATED leases
    if lease.status not in [LeaseStatus.DRAFT, LeaseStatus.TERMINATED]:
        raise ValidationError(
            f"Cannot delete lease in '{lease.status.value}' status. "
            "Only DRAFT or TERMINATED leases can be deleted."
        )

    await crud.delete_lease(db, lease)
    await db.commit()


# ----- Lease Term Services -----


async def add_lease_term(
    db: AsyncSession,
    lease_id: int,
    account_id: int,
    company_id: int,
    data: VendorLeaseTermCreate,
) -> VendorLease:
    """Add a new term to a lease (for renewals/adjustments)."""
    lease = await crud.get_lease_by_id(
        db, lease_id, account_id, company_id, include_details=True
    )
    if not lease:
        raise NotFoundError(f"Lease with ID {lease_id} not found")

    if lease.status != LeaseStatus.ACTIVE:
        raise ValidationError("Can only add terms to ACTIVE leases")

    # Get current max term number
    existing_terms = await crud.get_lease_terms(db, lease_id, account_id, company_id)
    max_term = max((t.term_number for t in existing_terms), default=0)

    if data.term_number != max_term + 1:
        raise ValidationError(f"Next term number should be {max_term + 1}")

    await crud.create_lease_term(
        db=db,
        account_id=account_id,
        company_id=company_id,
        lease_id=lease_id,
        term_number=data.term_number,
        start_date=data.start_date,
        end_date=data.end_date,
        rent_amount=data.rent_amount,
        reason=data.reason,
    )

    # Update lease end date and rent if term extends beyond current
    if data.end_date > lease.end_date:
        await crud.update_lease(db, lease, end_date=data.end_date)
    await crud.update_lease(db, lease, rent_amount=data.rent_amount)

    await db.commit()
    return await crud.get_lease_by_id(
        db, lease_id, account_id, company_id, include_details=True
    )


# ----- Lease Coverage Services -----


async def add_lease_coverage(
    db: AsyncSession,
    lease_id: int,
    account_id: int,
    company_id: int,
    data: VendorLeaseCoverageCreate,
) -> VendorLease:
    """Add coverage to a lease."""
    lease = await crud.get_lease_by_id(db, lease_id, account_id, company_id)
    if not lease:
        raise NotFoundError(f"Lease with ID {lease_id} not found")

    if lease.status not in [LeaseStatus.DRAFT, LeaseStatus.ACTIVE]:
        raise ValidationError("Can only add coverage to DRAFT or ACTIVE leases")

    # Validate based on scope type
    if data.scope_type == CoverageScope.PROPERTY:
        if not data.property_id:
            raise ValidationError("property_id is required for PROPERTY scope")
        # Verify property exists
        prop = await property_crud.get_property_by_id(
            db, data.property_id, account_id, company_id
        )
        if not prop:
            raise NotFoundError(f"Property with ID {data.property_id} not found")
        property_id = data.property_id
        unit_id = None
    elif data.scope_type == CoverageScope.UNIT:
        if not data.unit_id:
            raise ValidationError("unit_id is required for UNIT scope")
        # Verify unit exists
        unit = await property_crud.get_unit_by_id(
            db, data.unit_id, account_id, company_id
        )
        if not unit:
            raise NotFoundError(f"Unit with ID {data.unit_id} not found")
        property_id = unit.property_id
        unit_id = data.unit_id
    else:
        raise ValidationError(f"Invalid scope type: {data.scope_type}")

    await crud.create_lease_coverage(
        db=db,
        account_id=account_id,
        company_id=company_id,
        lease_id=lease_id,
        scope_type=data.scope_type,
        property_id=property_id,
        unit_id=unit_id,
    )

    await db.commit()
    return await crud.get_lease_by_id(
        db, lease_id, account_id, company_id, include_details=True
    )


async def remove_lease_coverage(
    db: AsyncSession,
    lease_id: int,
    coverage_id: int,
    account_id: int,
    company_id: int,
) -> VendorLease:
    """Remove coverage from a lease."""
    lease = await crud.get_lease_by_id(db, lease_id, account_id, company_id)
    if not lease:
        raise NotFoundError(f"Lease with ID {lease_id} not found")

    if lease.status != LeaseStatus.DRAFT:
        raise ValidationError("Can only remove coverage from DRAFT leases")

    coverage = await crud.get_coverage_by_id(db, coverage_id, account_id, company_id)
    if not coverage or coverage.lease_id != lease_id:
        raise NotFoundError(f"Coverage with ID {coverage_id} not found for this lease")

    await crud.delete_lease_coverage(db, coverage)

    await db.commit()
    return await crud.get_lease_by_id(
        db, lease_id, account_id, company_id, include_details=True
    )
