"""CRUD operations for vendor management module."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    CoverageScope,
    LeaseStatus,
    Vendor,
    VendorLease,
    VendorLeaseCoverage,
    VendorLeaseTerm,
    VendorStatus,
    VendorType,
)

# ----- Vendor CRUD -----


async def get_vendor_by_id(
    db: AsyncSession,
    vendor_id: int,
    account_id: int,
    company_id: int,
) -> Vendor | None:
    """Get a vendor by ID within tenant scope."""
    result = await db.execute(
        select(Vendor).where(
            and_(
                Vendor.id == vendor_id,
                Vendor.account_id == account_id,
                Vendor.company_id == company_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_vendor_by_code(
    db: AsyncSession,
    vendor_code: str,
    account_id: int,
    company_id: int,
) -> Vendor | None:
    """Get a vendor by code within tenant scope."""
    result = await db.execute(
        select(Vendor).where(
            and_(
                Vendor.vendor_code == vendor_code,
                Vendor.account_id == account_id,
                Vendor.company_id == company_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_vendors(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    skip: int = 0,
    limit: int = 100,
    status: VendorStatus | None = None,
    vendor_type: VendorType | None = None,
    search: str | None = None,
) -> tuple[list[Vendor], int]:
    """Get vendors with filtering and pagination."""
    base_filter = and_(
        Vendor.account_id == account_id,
        Vendor.company_id == company_id,
    )

    filters = [base_filter]
    if status:
        filters.append(Vendor.status == status)
    if vendor_type:
        filters.append(Vendor.vendor_type == vendor_type)
    if search:
        search_filter = f"%{search}%"
        filters.append(
            (Vendor.name.ilike(search_filter))
            | (Vendor.vendor_code.ilike(search_filter))
            | (Vendor.contact_name.ilike(search_filter))
        )

    # Count query
    count_query = select(func.count(Vendor.id)).where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Data query
    data_query = (
        select(Vendor)
        .where(and_(*filters))
        .order_by(Vendor.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(data_query)
    vendors = list(result.scalars().all())

    return vendors, total


async def create_vendor(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    vendor_code: str,
    name: str,
    vendor_type: VendorType,
    status: VendorStatus = VendorStatus.ACTIVE,
    **kwargs,
) -> Vendor:
    """Create a new vendor."""
    import uuid

    # Get next ID for this tenant
    result = await db.execute(
        select(Vendor.id)
        .where(and_(Vendor.account_id == account_id, Vendor.company_id == company_id))
        .order_by(Vendor.id.desc())
        .limit(1)
    )
    max_id = result.scalar_one_or_none()
    next_id = (max_id or 0) + 1

    vendor = Vendor(
        account_id=account_id,
        company_id=company_id,
        id=next_id,
        uuid=str(uuid.uuid4()),
        vendor_code=vendor_code,
        name=name,
        vendor_type=vendor_type,
        status=status,
        **kwargs,
    )
    db.add(vendor)
    await db.flush()
    return vendor


async def update_vendor(db: AsyncSession, vendor: Vendor, **kwargs) -> Vendor:
    """Update a vendor."""
    for key, value in kwargs.items():
        if value is not None and hasattr(vendor, key):
            setattr(vendor, key, value)
    await db.flush()
    return vendor


async def delete_vendor(db: AsyncSession, vendor: Vendor) -> None:
    """Delete a vendor (will cascade to leases)."""
    await db.delete(vendor)
    await db.flush()


# ----- Vendor Lease CRUD -----


async def get_lease_by_id(
    db: AsyncSession,
    lease_id: int,
    account_id: int,
    company_id: int,
    include_details: bool = False,
) -> VendorLease | None:
    """Get a vendor lease by ID within tenant scope."""
    query = select(VendorLease).where(
        and_(
            VendorLease.id == lease_id,
            VendorLease.account_id == account_id,
            VendorLease.company_id == company_id,
        )
    )
    if include_details:
        query = query.options(
            selectinload(VendorLease.vendor),
            selectinload(VendorLease.terms),
            selectinload(VendorLease.coverages),
        )
    else:
        query = query.options(selectinload(VendorLease.vendor))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_lease_by_code(
    db: AsyncSession,
    lease_code: str,
    account_id: int,
    company_id: int,
) -> VendorLease | None:
    """Get a vendor lease by code within tenant scope."""
    result = await db.execute(
        select(VendorLease).where(
            and_(
                VendorLease.lease_code == lease_code,
                VendorLease.account_id == account_id,
                VendorLease.company_id == company_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_leases(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    skip: int = 0,
    limit: int = 100,
    vendor_id: int | None = None,
    status: LeaseStatus | None = None,
    search: str | None = None,
) -> tuple[list[VendorLease], int]:
    """Get vendor leases with filtering and pagination."""
    base_filter = and_(
        VendorLease.account_id == account_id,
        VendorLease.company_id == company_id,
    )

    filters = [base_filter]
    if vendor_id:
        filters.append(VendorLease.vendor_id == vendor_id)
    if status:
        filters.append(VendorLease.status == status)
    if search:
        search_filter = f"%{search}%"
        filters.append(
            (VendorLease.lease_code.ilike(search_filter))
            | (VendorLease.description.ilike(search_filter))
        )

    # Count query
    count_query = select(func.count(VendorLease.id)).where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Data query
    data_query = (
        select(VendorLease)
        .options(selectinload(VendorLease.vendor))
        .where(and_(*filters))
        .order_by(VendorLease.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(data_query)
    leases = list(result.scalars().all())

    return leases, total


async def create_lease(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    vendor_id: int,
    lease_code: str,
    start_date: date,
    end_date: date,
    rent_amount: Decimal,
    currency: str = "AED",
    **kwargs,
) -> VendorLease:
    """Create a new vendor lease."""
    import uuid

    # Get next ID for this tenant
    result = await db.execute(
        select(VendorLease.id)
        .where(
            and_(
                VendorLease.account_id == account_id,
                VendorLease.company_id == company_id,
            )
        )
        .order_by(VendorLease.id.desc())
        .limit(1)
    )
    max_id = result.scalar_one_or_none()
    next_id = (max_id or 0) + 1

    lease = VendorLease(
        account_id=account_id,
        company_id=company_id,
        id=next_id,
        uuid=str(uuid.uuid4()),
        vendor_id=vendor_id,
        lease_code=lease_code,
        start_date=start_date,
        end_date=end_date,
        rent_amount=rent_amount,
        currency=currency,
        status=LeaseStatus.DRAFT,
        **kwargs,
    )
    db.add(lease)
    await db.flush()
    return lease


async def update_lease(db: AsyncSession, lease: VendorLease, **kwargs) -> VendorLease:
    """Update a vendor lease."""
    for key, value in kwargs.items():
        if value is not None and hasattr(lease, key):
            setattr(lease, key, value)
    await db.flush()
    return lease


async def activate_lease(db: AsyncSession, lease: VendorLease) -> VendorLease:
    """Activate a vendor lease."""
    lease.status = LeaseStatus.ACTIVE
    lease.activated_at = datetime.now(timezone.utc)
    await db.flush()
    return lease


async def terminate_lease(
    db: AsyncSession, lease: VendorLease, reason: str
) -> VendorLease:
    """Terminate a vendor lease."""
    lease.status = LeaseStatus.TERMINATED
    lease.terminated_at = datetime.now(timezone.utc)
    lease.termination_reason = reason
    await db.flush()
    return lease


async def delete_lease(db: AsyncSession, lease: VendorLease) -> None:
    """Delete a vendor lease (will cascade to terms and coverage)."""
    await db.delete(lease)
    await db.flush()


# ----- Vendor Lease Term CRUD -----


async def get_lease_terms(
    db: AsyncSession,
    lease_id: int,
    account_id: int,
    company_id: int,
) -> list[VendorLeaseTerm]:
    """Get all terms for a lease."""
    result = await db.execute(
        select(VendorLeaseTerm)
        .where(
            and_(
                VendorLeaseTerm.lease_id == lease_id,
                VendorLeaseTerm.account_id == account_id,
                VendorLeaseTerm.company_id == company_id,
            )
        )
        .order_by(VendorLeaseTerm.term_number)
    )
    return list(result.scalars().all())


async def create_lease_term(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    lease_id: int,
    term_number: int,
    start_date: date,
    end_date: date,
    rent_amount: Decimal,
    reason: str | None = None,
) -> VendorLeaseTerm:
    """Create a new lease term."""
    import uuid

    # Get next ID for this tenant
    result = await db.execute(
        select(VendorLeaseTerm.id)
        .where(
            and_(
                VendorLeaseTerm.account_id == account_id,
                VendorLeaseTerm.company_id == company_id,
            )
        )
        .order_by(VendorLeaseTerm.id.desc())
        .limit(1)
    )
    max_id = result.scalar_one_or_none()
    next_id = (max_id or 0) + 1

    term = VendorLeaseTerm(
        account_id=account_id,
        company_id=company_id,
        id=next_id,
        uuid=str(uuid.uuid4()),
        lease_id=lease_id,
        term_number=term_number,
        start_date=start_date,
        end_date=end_date,
        rent_amount=rent_amount,
        reason=reason,
    )
    db.add(term)
    await db.flush()
    return term


# ----- Vendor Lease Coverage CRUD -----


async def get_lease_coverages(
    db: AsyncSession,
    lease_id: int,
    account_id: int,
    company_id: int,
) -> list[VendorLeaseCoverage]:
    """Get all coverage entries for a lease."""
    result = await db.execute(
        select(VendorLeaseCoverage).where(
            and_(
                VendorLeaseCoverage.lease_id == lease_id,
                VendorLeaseCoverage.account_id == account_id,
                VendorLeaseCoverage.company_id == company_id,
            )
        )
    )
    return list(result.scalars().all())


async def create_lease_coverage(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    lease_id: int,
    scope_type: CoverageScope,
    property_id: int | None = None,
    unit_id: int | None = None,
) -> VendorLeaseCoverage:
    """Create a new lease coverage entry."""
    import uuid

    # Get next ID for this tenant
    result = await db.execute(
        select(VendorLeaseCoverage.id)
        .where(
            and_(
                VendorLeaseCoverage.account_id == account_id,
                VendorLeaseCoverage.company_id == company_id,
            )
        )
        .order_by(VendorLeaseCoverage.id.desc())
        .limit(1)
    )
    max_id = result.scalar_one_or_none()
    next_id = (max_id or 0) + 1

    coverage = VendorLeaseCoverage(
        account_id=account_id,
        company_id=company_id,
        id=next_id,
        uuid=str(uuid.uuid4()),
        lease_id=lease_id,
        scope_type=scope_type,
        property_id=property_id,
        unit_id=unit_id,
    )
    db.add(coverage)
    await db.flush()
    return coverage


async def delete_lease_coverage(
    db: AsyncSession, coverage: VendorLeaseCoverage
) -> None:
    """Delete a lease coverage entry."""
    await db.delete(coverage)
    await db.flush()


async def get_coverage_by_id(
    db: AsyncSession,
    coverage_id: int,
    account_id: int,
    company_id: int,
) -> VendorLeaseCoverage | None:
    """Get a coverage entry by ID."""
    result = await db.execute(
        select(VendorLeaseCoverage).where(
            and_(
                VendorLeaseCoverage.id == coverage_id,
                VendorLeaseCoverage.account_id == account_id,
                VendorLeaseCoverage.company_id == company_id,
            )
        )
    )
    return result.scalar_one_or_none()
