"""EP-01, EP-02, EP-03 Specification Alignment

Revision ID: 0002
Revises: 0001
Create Date: 2024-12-08

Aligns database schema with EP specification documents:
- EP-01: Property & Unit Management (no changes needed)
- EP-02: Vendor & Vendor Lease Management (new fields)
- EP-03: Tenant Management & KYC (new fields, enum changes)

Changes:
- document_types: Add document_category, is_expiry_required, sort_order
- tenants: Add gender, occupation, employer_name, trade_name, emergency contact,
           preferred_language, source, next_doc_expiry_date, blacklist fields,
           active_contracts_count; Update kyc_status enum values
- tenant_contacts: Add status column
- tenant_documents: Add is_primary; Update verification_status enum values
- vendor_leases: Add payment_day, escalation_type, escalation_value,
                 notice_period_days, auto_renew, termination_date,
                 terminated_by_id, total_covered_units
- vendor_lease_terms: Add rent_change_pct, approved_by_id, approved_at
- vendor_lease_coverages: Add covered_from, covered_to, rent_allocation
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new columns and update enums for EP spec alignment."""

    # =====================
    # DOCUMENT_TYPES TABLE
    # =====================

    # Add document_category enum column
    op.execute("""
        ALTER TABLE document_types
        ADD COLUMN document_category ENUM('identity', 'residency', 'business', 'financial', 'other') NULL
        AFTER description
    """)

    # Add is_expiry_required column
    op.execute("""
        ALTER TABLE document_types
        ADD COLUMN is_expiry_required BOOLEAN NOT NULL DEFAULT FALSE
        AFTER is_mandatory
    """)

    # Add sort_order column
    op.execute("""
        ALTER TABLE document_types
        ADD COLUMN sort_order INT NOT NULL DEFAULT 0
        AFTER is_expiry_required
    """)

    # Update existing document types with appropriate categories
    op.execute("""
        UPDATE document_types SET
            document_category = CASE
                WHEN code IN ('PASSPORT', 'EMIRATES_ID', 'PHOTO') THEN 'identity'
                WHEN code IN ('VISA', 'TENANCY_CONTRACT') THEN 'residency'
                WHEN code IN ('TRADE_LICENSE', 'MEMORANDUM', 'POWER_OF_ATTORNEY', 'VAT_CERTIFICATE') THEN 'business'
                WHEN code IN ('BANK_STATEMENT', 'SALARY_CERTIFICATE', 'EMPLOYMENT_CONTRACT') THEN 'financial'
                ELSE 'other'
            END,
            is_expiry_required = CASE
                WHEN code IN ('PASSPORT', 'EMIRATES_ID', 'VISA', 'TRADE_LICENSE') THEN TRUE
                ELSE FALSE
            END,
            sort_order = CASE
                WHEN code = 'PASSPORT' THEN 1
                WHEN code = 'EMIRATES_ID' THEN 2
                WHEN code = 'VISA' THEN 3
                WHEN code = 'PHOTO' THEN 4
                WHEN code = 'TRADE_LICENSE' THEN 5
                WHEN code = 'MEMORANDUM' THEN 6
                WHEN code = 'POWER_OF_ATTORNEY' THEN 7
                WHEN code = 'VAT_CERTIFICATE' THEN 8
                WHEN code = 'BANK_STATEMENT' THEN 9
                WHEN code = 'SALARY_CERTIFICATE' THEN 10
                WHEN code = 'EMPLOYMENT_CONTRACT' THEN 11
                WHEN code = 'TENANCY_CONTRACT' THEN 12
                ELSE 99
            END
    """)

    # =====================
    # TENANTS TABLE
    # =====================

    # Add gender enum column
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN gender ENUM('male', 'female', 'other') NULL
        AFTER date_of_birth
    """)

    # Add occupation column
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN occupation VARCHAR(120) NULL
        AFTER emirates_id
    """)

    # Add employer_name column
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN employer_name VARCHAR(255) NULL
        AFTER occupation
    """)

    # Add trade_name column (for entities)
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN trade_name VARCHAR(255) NULL
        AFTER entity_name
    """)

    # Add emergency contact fields
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN emergency_contact_name VARCHAR(255) NULL
        AFTER country
    """)

    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN emergency_contact_phone VARCHAR(50) NULL
        AFTER emergency_contact_name
    """)

    # Add preferred_language column
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN preferred_language VARCHAR(10) NULL
        AFTER emergency_contact_phone
    """)

    # Add source column (referral source)
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN source VARCHAR(120) NULL
        AFTER preferred_language
    """)

    # Add next_doc_expiry_date column
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN next_doc_expiry_date DATE NULL
        AFTER kyc_verified_by_id
    """)

    # Add blacklist fields
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN blacklist_reason TEXT NULL
        AFTER notes
    """)

    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN blacklisted_at DATETIME(6) NULL
        AFTER blacklist_reason
    """)

    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN blacklisted_by_id INT NULL
        AFTER blacklisted_at
    """)

    # Add active_contracts_count column
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN active_contracts_count INT NOT NULL DEFAULT 0
        AFTER blacklisted_by_id
    """)

    # Update kyc_status enum to match EP-03 spec
    # MySQL requires recreating the column with new enum values
    # First add a temp column, copy data, drop old, rename new
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN kyc_status_new ENUM(
            'not_started', 'incomplete', 'pending_verification',
            'verified', 'expired', 'rejected'
        ) NOT NULL DEFAULT 'not_started'
        AFTER source
    """)

    # Map old values to new values
    op.execute("""
        UPDATE tenants SET kyc_status_new = CASE kyc_status
            WHEN 'pending' THEN 'not_started'
            WHEN 'in_progress' THEN 'incomplete'
            WHEN 'verified' THEN 'verified'
            WHEN 'rejected' THEN 'rejected'
            WHEN 'expired' THEN 'expired'
            ELSE 'not_started'
        END
    """)

    # Drop old column and rename new
    op.execute("ALTER TABLE tenants DROP COLUMN kyc_status")
    op.execute("ALTER TABLE tenants CHANGE kyc_status_new kyc_status ENUM('not_started', 'incomplete', 'pending_verification', 'verified', 'expired', 'rejected') NOT NULL DEFAULT 'not_started'")

    # Recreate the index on kyc_status
    op.execute("CREATE INDEX ix_tenants_kyc_status_new ON tenants (account_id, company_id, kyc_status)")
    op.execute("DROP INDEX ix_tenants_kyc_status ON tenants")
    op.execute("ALTER TABLE tenants RENAME INDEX ix_tenants_kyc_status_new TO ix_tenants_kyc_status")

    # =====================
    # TENANT_CONTACTS TABLE
    # =====================

    # Add status column
    op.execute("""
        ALTER TABLE tenant_contacts
        ADD COLUMN status ENUM('active', 'inactive') NOT NULL DEFAULT 'active'
        AFTER is_primary
    """)

    # =====================
    # TENANT_DOCUMENTS TABLE
    # =====================

    # Add is_primary column
    op.execute("""
        ALTER TABLE tenant_documents
        ADD COLUMN is_primary BOOLEAN NOT NULL DEFAULT FALSE
        AFTER rejection_reason
    """)

    # Update verification_status enum to match EP-03 spec
    op.execute("""
        ALTER TABLE tenant_documents
        ADD COLUMN verification_status_new ENUM(
            'not_uploaded', 'uploaded', 'under_review', 'verified', 'rejected'
        ) NOT NULL DEFAULT 'not_uploaded'
        AFTER mime_type
    """)

    # Map old values to new values
    op.execute("""
        UPDATE tenant_documents SET verification_status_new = CASE verification_status
            WHEN 'pending' THEN 'uploaded'
            WHEN 'verified' THEN 'verified'
            WHEN 'rejected' THEN 'rejected'
            WHEN 'expired' THEN 'rejected'
            ELSE 'not_uploaded'
        END
    """)

    # Drop old column and rename new
    op.execute("ALTER TABLE tenant_documents DROP COLUMN verification_status")
    op.execute("ALTER TABLE tenant_documents CHANGE verification_status_new verification_status ENUM('not_uploaded', 'uploaded', 'under_review', 'verified', 'rejected') NOT NULL DEFAULT 'not_uploaded'")

    # Recreate the index on verification_status
    op.execute("CREATE INDEX ix_tenant_documents_status_new ON tenant_documents (account_id, company_id, verification_status)")
    op.execute("DROP INDEX ix_tenant_documents_status ON tenant_documents")
    op.execute("ALTER TABLE tenant_documents RENAME INDEX ix_tenant_documents_status_new TO ix_tenant_documents_status")

    # =====================
    # VENDOR_LEASES TABLE
    # =====================

    # Add payment_day column
    op.execute("""
        ALTER TABLE vendor_leases
        ADD COLUMN payment_day INT NULL
        AFTER billing_cycle
    """)

    # Add escalation_type enum column
    op.execute("""
        ALTER TABLE vendor_leases
        ADD COLUMN escalation_type ENUM('none', 'fixed_amount', 'percentage', 'cpi_linked')
            NOT NULL DEFAULT 'none'
        AFTER security_deposit
    """)

    # Add escalation_value column
    op.execute("""
        ALTER TABLE vendor_leases
        ADD COLUMN escalation_value DECIMAL(15, 2) NULL
        AFTER escalation_type
    """)

    # Add notice_period_days column
    op.execute("""
        ALTER TABLE vendor_leases
        ADD COLUMN notice_period_days INT NULL
        AFTER escalation_value
    """)

    # Add auto_renew column
    op.execute("""
        ALTER TABLE vendor_leases
        ADD COLUMN auto_renew BOOLEAN NOT NULL DEFAULT FALSE
        AFTER notice_period_days
    """)

    # Add termination_date column
    op.execute("""
        ALTER TABLE vendor_leases
        ADD COLUMN termination_date DATE NULL
        AFTER terminated_at
    """)

    # Add terminated_by_id column
    op.execute("""
        ALTER TABLE vendor_leases
        ADD COLUMN terminated_by_id INT NULL
        AFTER termination_reason
    """)

    # Add total_covered_units column
    op.execute("""
        ALTER TABLE vendor_leases
        ADD COLUMN total_covered_units INT NOT NULL DEFAULT 0
        AFTER terminated_by_id
    """)

    # =====================
    # VENDOR_LEASE_TERMS TABLE
    # =====================

    # Add rent_change_pct column
    op.execute("""
        ALTER TABLE vendor_lease_terms
        ADD COLUMN rent_change_pct DECIMAL(5, 2) NULL
        AFTER rent_amount
    """)

    # Add approved_by_id column
    op.execute("""
        ALTER TABLE vendor_lease_terms
        ADD COLUMN approved_by_id INT NULL
        AFTER reason
    """)

    # Add approved_at column
    op.execute("""
        ALTER TABLE vendor_lease_terms
        ADD COLUMN approved_at DATETIME(6) NULL
        AFTER approved_by_id
    """)

    # =====================
    # VENDOR_LEASE_COVERAGES TABLE
    # =====================

    # Add covered_from column
    op.execute("""
        ALTER TABLE vendor_lease_coverages
        ADD COLUMN covered_from DATE NULL
        AFTER unit_id
    """)

    # Add covered_to column
    op.execute("""
        ALTER TABLE vendor_lease_coverages
        ADD COLUMN covered_to DATE NULL
        AFTER covered_from
    """)

    # Add rent_allocation column
    op.execute("""
        ALTER TABLE vendor_lease_coverages
        ADD COLUMN rent_allocation DECIMAL(15, 2) NULL
        AFTER covered_to
    """)


def downgrade() -> None:
    """Remove columns added for EP spec alignment."""

    # =====================
    # VENDOR_LEASE_COVERAGES TABLE
    # =====================
    op.execute("ALTER TABLE vendor_lease_coverages DROP COLUMN rent_allocation")
    op.execute("ALTER TABLE vendor_lease_coverages DROP COLUMN covered_to")
    op.execute("ALTER TABLE vendor_lease_coverages DROP COLUMN covered_from")

    # =====================
    # VENDOR_LEASE_TERMS TABLE
    # =====================
    op.execute("ALTER TABLE vendor_lease_terms DROP COLUMN approved_at")
    op.execute("ALTER TABLE vendor_lease_terms DROP COLUMN approved_by_id")
    op.execute("ALTER TABLE vendor_lease_terms DROP COLUMN rent_change_pct")

    # =====================
    # VENDOR_LEASES TABLE
    # =====================
    op.execute("ALTER TABLE vendor_leases DROP COLUMN total_covered_units")
    op.execute("ALTER TABLE vendor_leases DROP COLUMN terminated_by_id")
    op.execute("ALTER TABLE vendor_leases DROP COLUMN termination_date")
    op.execute("ALTER TABLE vendor_leases DROP COLUMN auto_renew")
    op.execute("ALTER TABLE vendor_leases DROP COLUMN notice_period_days")
    op.execute("ALTER TABLE vendor_leases DROP COLUMN escalation_value")
    op.execute("ALTER TABLE vendor_leases DROP COLUMN escalation_type")
    op.execute("ALTER TABLE vendor_leases DROP COLUMN payment_day")

    # =====================
    # TENANT_DOCUMENTS TABLE
    # =====================
    op.execute("ALTER TABLE tenant_documents DROP COLUMN is_primary")

    # Revert verification_status enum
    op.execute("""
        ALTER TABLE tenant_documents
        ADD COLUMN verification_status_old ENUM('pending', 'verified', 'rejected', 'expired')
            NOT NULL DEFAULT 'pending'
        AFTER mime_type
    """)
    op.execute("""
        UPDATE tenant_documents SET verification_status_old = CASE verification_status
            WHEN 'not_uploaded' THEN 'pending'
            WHEN 'uploaded' THEN 'pending'
            WHEN 'under_review' THEN 'pending'
            WHEN 'verified' THEN 'verified'
            WHEN 'rejected' THEN 'rejected'
            ELSE 'pending'
        END
    """)
    op.execute("DROP INDEX ix_tenant_documents_status ON tenant_documents")
    op.execute("ALTER TABLE tenant_documents DROP COLUMN verification_status")
    op.execute("ALTER TABLE tenant_documents CHANGE verification_status_old verification_status ENUM('pending', 'verified', 'rejected', 'expired') NOT NULL DEFAULT 'pending'")
    op.execute("CREATE INDEX ix_tenant_documents_status ON tenant_documents (account_id, company_id, verification_status)")

    # =====================
    # TENANT_CONTACTS TABLE
    # =====================
    op.execute("ALTER TABLE tenant_contacts DROP COLUMN status")

    # =====================
    # TENANTS TABLE
    # =====================
    op.execute("ALTER TABLE tenants DROP COLUMN active_contracts_count")
    op.execute("ALTER TABLE tenants DROP COLUMN blacklisted_by_id")
    op.execute("ALTER TABLE tenants DROP COLUMN blacklisted_at")
    op.execute("ALTER TABLE tenants DROP COLUMN blacklist_reason")
    op.execute("ALTER TABLE tenants DROP COLUMN next_doc_expiry_date")
    op.execute("ALTER TABLE tenants DROP COLUMN source")
    op.execute("ALTER TABLE tenants DROP COLUMN preferred_language")
    op.execute("ALTER TABLE tenants DROP COLUMN emergency_contact_phone")
    op.execute("ALTER TABLE tenants DROP COLUMN emergency_contact_name")
    op.execute("ALTER TABLE tenants DROP COLUMN trade_name")
    op.execute("ALTER TABLE tenants DROP COLUMN employer_name")
    op.execute("ALTER TABLE tenants DROP COLUMN occupation")
    op.execute("ALTER TABLE tenants DROP COLUMN gender")

    # Revert kyc_status enum
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN kyc_status_old ENUM('pending', 'in_progress', 'verified', 'rejected', 'expired')
            NOT NULL DEFAULT 'pending'
        AFTER source
    """)
    op.execute("""
        UPDATE tenants SET kyc_status_old = CASE kyc_status
            WHEN 'not_started' THEN 'pending'
            WHEN 'incomplete' THEN 'in_progress'
            WHEN 'pending_verification' THEN 'in_progress'
            WHEN 'verified' THEN 'verified'
            WHEN 'rejected' THEN 'rejected'
            WHEN 'expired' THEN 'expired'
            ELSE 'pending'
        END
    """)
    op.execute("DROP INDEX ix_tenants_kyc_status ON tenants")
    op.execute("ALTER TABLE tenants DROP COLUMN kyc_status")
    op.execute("ALTER TABLE tenants CHANGE kyc_status_old kyc_status ENUM('pending', 'in_progress', 'verified', 'rejected', 'expired') NOT NULL DEFAULT 'pending'")
    op.execute("CREATE INDEX ix_tenants_kyc_status ON tenants (account_id, company_id, kyc_status)")

    # =====================
    # DOCUMENT_TYPES TABLE
    # =====================
    op.execute("ALTER TABLE document_types DROP COLUMN sort_order")
    op.execute("ALTER TABLE document_types DROP COLUMN is_expiry_required")
    op.execute("ALTER TABLE document_types DROP COLUMN document_category")
