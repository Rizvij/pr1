"""Schema Field Alignment with EP Specifications

Revision ID: 0003
Revises: 0002
Create Date: 2024-12-10

Aligns field names and adds missing columns per EP-01, EP-02, EP-03 specs:

EP-01 Changes:
- properties: Rename name->property_name, address->address_line_1, add address_line_2,
              total_units_count, active_units_count
- units: Rename name->display_name, area_sqft->area_sqm, add room_number, sort_order,
         change floor_number to VARCHAR(10)
- unit_categories: Add is_residential, is_commercial, allowed_parent_categories, max_depth

EP-02 Changes:
- vendors: Rename name->vendor_name, address->address_line_1, phone->contact_phone,
           email->contact_email, add address_line_2, active_leases_count,
           change vendor_type enum to INDIVIDUAL/COMPANY
- vendor_lease_terms: Add status enum, notes column, change reason to enum
- vendor_lease_coverages: Add notes column

EP-03 Changes:
- tenants: Rename email->primary_email, phone->primary_phone, address->address_line_1,
           add address_line_2, full_name
- tenant_documents: Rename file_path->file_reference, file_size->file_size_kb,
                    mime_type->file_type
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply schema field alignment changes."""

    # =====================
    # EP-01: UNIT_CATEGORIES TABLE
    # =====================

    op.execute("""
        ALTER TABLE unit_categories
        ADD COLUMN is_residential BOOLEAN NOT NULL DEFAULT FALSE
        AFTER description
    """)

    op.execute("""
        ALTER TABLE unit_categories
        ADD COLUMN is_commercial BOOLEAN NOT NULL DEFAULT FALSE
        AFTER is_residential
    """)

    op.execute("""
        ALTER TABLE unit_categories
        ADD COLUMN allowed_parent_categories TEXT NULL
        AFTER is_commercial
    """)

    op.execute("""
        ALTER TABLE unit_categories
        ADD COLUMN max_depth INT NOT NULL DEFAULT 1
        AFTER allowed_parent_categories
    """)

    # Update existing categories with appropriate flags
    op.execute("""
        UPDATE unit_categories SET
            is_residential = CASE
                WHEN code IN ('APARTMENT', 'BEDSPACE', 'STUDIO', 'VILLA', 'ROOM') THEN TRUE
                ELSE FALSE
            END,
            is_commercial = CASE
                WHEN code IN ('SHOP', 'OFFICE', 'WAREHOUSE', 'RETAIL', 'KIOSK') THEN TRUE
                ELSE FALSE
            END,
            allowed_parent_categories = CASE
                WHEN code = 'BEDSPACE' THEN '["APARTMENT", "ROOM"]'
                WHEN code = 'ROOM' THEN '["APARTMENT", "FLOOR"]'
                WHEN code = 'APARTMENT' THEN '["FLOOR", "BUILDING"]'
                WHEN code = 'SHOP' THEN '["FLOOR", "BUILDING"]'
                WHEN code = 'OFFICE' THEN '["FLOOR", "BUILDING"]'
                ELSE NULL
            END,
            max_depth = CASE
                WHEN code = 'BEDSPACE' THEN 3
                WHEN code IN ('APARTMENT', 'SHOP', 'OFFICE') THEN 2
                ELSE 1
            END
    """)

    # =====================
    # EP-01: PROPERTIES TABLE
    # =====================

    # Rename name to property_name
    op.execute("""
        ALTER TABLE properties
        CHANGE COLUMN name property_name VARCHAR(255) NOT NULL
    """)

    # Rename address to address_line_1 and make it NOT NULL with default
    op.execute("""
        ALTER TABLE properties
        CHANGE COLUMN address address_line_1 VARCHAR(255) NOT NULL DEFAULT ''
    """)

    # Add address_line_2
    op.execute("""
        ALTER TABLE properties
        ADD COLUMN address_line_2 VARCHAR(255) NULL
        AFTER address_line_1
    """)

    # Add total_units_count
    op.execute("""
        ALTER TABLE properties
        ADD COLUMN total_units_count INT NOT NULL DEFAULT 0
        AFTER year_built
    """)

    # Add active_units_count
    op.execute("""
        ALTER TABLE properties
        ADD COLUMN active_units_count INT NOT NULL DEFAULT 0
        AFTER total_units_count
    """)

    # =====================
    # EP-01: UNITS TABLE
    # =====================

    # Rename name to display_name (nullable per spec)
    op.execute("""
        ALTER TABLE units
        CHANGE COLUMN name display_name VARCHAR(255) NULL
    """)

    # Change floor_number from INT to VARCHAR(10) per spec
    op.execute("""
        ALTER TABLE units
        MODIFY COLUMN floor_number VARCHAR(10) NULL
    """)

    # Add room_number
    op.execute("""
        ALTER TABLE units
        ADD COLUMN room_number VARCHAR(20) NULL
        AFTER floor_number
    """)

    # Rename area_sqft to area_sqm
    op.execute("""
        ALTER TABLE units
        CHANGE COLUMN area_sqft area_sqm DECIMAL(10, 2) NULL
    """)

    # Add sort_order
    op.execute("""
        ALTER TABLE units
        ADD COLUMN sort_order INT NOT NULL DEFAULT 0
        AFTER is_leaf
    """)

    # Update capacity to have default 1 and NOT NULL
    op.execute("""
        ALTER TABLE units
        MODIFY COLUMN capacity INT NOT NULL DEFAULT 1
    """)

    # =====================
    # EP-02: VENDORS TABLE
    # =====================

    # Rename name to vendor_name
    op.execute("""
        ALTER TABLE vendors
        CHANGE COLUMN name vendor_name VARCHAR(255) NOT NULL
    """)

    # Rename phone to contact_phone
    op.execute("""
        ALTER TABLE vendors
        CHANGE COLUMN phone contact_phone VARCHAR(50) NULL
    """)

    # Rename email to contact_email
    op.execute("""
        ALTER TABLE vendors
        CHANGE COLUMN email contact_email VARCHAR(255) NULL
    """)

    # Rename address to address_line_1
    op.execute("""
        ALTER TABLE vendors
        CHANGE COLUMN address address_line_1 VARCHAR(255) NULL
    """)

    # Add address_line_2
    op.execute("""
        ALTER TABLE vendors
        ADD COLUMN address_line_2 VARCHAR(255) NULL
        AFTER address_line_1
    """)

    # Drop mobile column (merged into contact_phone per spec)
    op.execute("""
        ALTER TABLE vendors
        DROP COLUMN mobile
    """)

    # Add active_leases_count
    op.execute("""
        ALTER TABLE vendors
        ADD COLUMN active_leases_count INT NOT NULL DEFAULT 0
        AFTER tax_registration_number
    """)

    # Change vendor_type enum to INDIVIDUAL/COMPANY per EP-02 spec
    op.execute("""
        ALTER TABLE vendors
        ADD COLUMN vendor_type_new ENUM('individual', 'company')
            NOT NULL DEFAULT 'individual'
        AFTER vendor_code
    """)

    # Map old values to new - all old types map to COMPANY except OTHER
    op.execute("""
        UPDATE vendors SET vendor_type_new = CASE vendor_type
            WHEN 'other' THEN 'individual'
            ELSE 'company'
        END
    """)

    # Drop old column and rename new
    op.execute("ALTER TABLE vendors DROP COLUMN vendor_type")
    op.execute("""
        ALTER TABLE vendors
        CHANGE vendor_type_new vendor_type ENUM('individual', 'company')
            NOT NULL DEFAULT 'individual'
    """)

    # Recreate index on vendor_type
    op.execute("DROP INDEX ix_vendors_type ON vendors")
    op.execute("CREATE INDEX ix_vendors_type ON vendors (account_id, company_id, vendor_type)")

    # =====================
    # EP-02: VENDOR_LEASE_TERMS TABLE
    # =====================

    # Add status enum column
    op.execute("""
        ALTER TABLE vendor_lease_terms
        ADD COLUMN status ENUM('active', 'expired', 'future')
            NOT NULL DEFAULT 'active'
        AFTER rent_change_pct
    """)

    # Change reason column to enum type
    op.execute("""
        ALTER TABLE vendor_lease_terms
        ADD COLUMN reason_new ENUM('initial', 'renewal', 'amendment') NULL
        AFTER status
    """)

    # Map existing text reasons to enum
    op.execute("""
        UPDATE vendor_lease_terms SET reason_new = CASE
            WHEN LOWER(reason) LIKE '%initial%' THEN 'initial'
            WHEN LOWER(reason) LIKE '%renew%' THEN 'renewal'
            WHEN LOWER(reason) LIKE '%amend%' THEN 'amendment'
            ELSE 'initial'
        END
        WHERE reason IS NOT NULL
    """)

    # Drop old reason and rename
    op.execute("ALTER TABLE vendor_lease_terms DROP COLUMN reason")
    op.execute("""
        ALTER TABLE vendor_lease_terms
        CHANGE reason_new reason ENUM('initial', 'renewal', 'amendment') NULL
    """)

    # Add notes column
    op.execute("""
        ALTER TABLE vendor_lease_terms
        ADD COLUMN notes TEXT NULL
        AFTER approved_at
    """)

    # =====================
    # EP-02: VENDOR_LEASE_COVERAGES TABLE
    # =====================

    # Add notes column
    op.execute("""
        ALTER TABLE vendor_lease_coverages
        ADD COLUMN notes VARCHAR(500) NULL
        AFTER rent_allocation
    """)

    # =====================
    # EP-03: TENANTS TABLE
    # =====================

    # Rename email to primary_email
    op.execute("""
        ALTER TABLE tenants
        CHANGE COLUMN email primary_email VARCHAR(255) NULL
    """)

    # Rename phone to primary_phone
    op.execute("""
        ALTER TABLE tenants
        CHANGE COLUMN phone primary_phone VARCHAR(50) NULL
    """)

    # Rename address to address_line_1
    op.execute("""
        ALTER TABLE tenants
        CHANGE COLUMN address address_line_1 VARCHAR(255) NULL
    """)

    # Add address_line_2
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN address_line_2 VARCHAR(255) NULL
        AFTER address_line_1
    """)

    # Add full_name column (stored/computed per spec)
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN full_name VARCHAR(255) NULL
        AFTER last_name
    """)

    # Populate full_name from first_name + last_name for individuals
    op.execute("""
        UPDATE tenants
        SET full_name = CASE
            WHEN tenant_type = 'individual' THEN
                TRIM(CONCAT(COALESCE(first_name, ''), ' ', COALESCE(last_name, '')))
            ELSE entity_name
        END
    """)

    # =====================
    # EP-03: TENANT_DOCUMENTS TABLE
    # =====================

    # Rename file_path to file_reference
    op.execute("""
        ALTER TABLE tenant_documents
        CHANGE COLUMN file_path file_reference VARCHAR(500) NULL
    """)

    # Rename file_size to file_size_kb
    op.execute("""
        ALTER TABLE tenant_documents
        CHANGE COLUMN file_size file_size_kb INT NULL
    """)

    # Rename mime_type to file_type
    op.execute("""
        ALTER TABLE tenant_documents
        CHANGE COLUMN mime_type file_type VARCHAR(100) NULL
    """)


def downgrade() -> None:
    """Revert schema field alignment changes."""

    # =====================
    # EP-03: TENANT_DOCUMENTS TABLE
    # =====================
    op.execute("ALTER TABLE tenant_documents CHANGE COLUMN file_type mime_type VARCHAR(100) NULL")
    op.execute("ALTER TABLE tenant_documents CHANGE COLUMN file_size_kb file_size INT NULL")
    op.execute("ALTER TABLE tenant_documents CHANGE COLUMN file_reference file_path VARCHAR(500) NULL")

    # =====================
    # EP-03: TENANTS TABLE
    # =====================
    op.execute("ALTER TABLE tenants DROP COLUMN full_name")
    op.execute("ALTER TABLE tenants DROP COLUMN address_line_2")
    op.execute("ALTER TABLE tenants CHANGE COLUMN address_line_1 address TEXT NULL")
    op.execute("ALTER TABLE tenants CHANGE COLUMN primary_phone phone VARCHAR(50) NULL")
    op.execute("ALTER TABLE tenants CHANGE COLUMN primary_email email VARCHAR(255) NULL")

    # =====================
    # EP-02: VENDOR_LEASE_COVERAGES TABLE
    # =====================
    op.execute("ALTER TABLE vendor_lease_coverages DROP COLUMN notes")

    # =====================
    # EP-02: VENDOR_LEASE_TERMS TABLE
    # =====================
    op.execute("ALTER TABLE vendor_lease_terms DROP COLUMN notes")
    op.execute("""
        ALTER TABLE vendor_lease_terms
        ADD COLUMN reason_old TEXT NULL AFTER status
    """)
    op.execute("""
        UPDATE vendor_lease_terms SET reason_old = reason
    """)
    op.execute("ALTER TABLE vendor_lease_terms DROP COLUMN reason")
    op.execute("ALTER TABLE vendor_lease_terms CHANGE reason_old reason TEXT NULL")
    op.execute("ALTER TABLE vendor_lease_terms DROP COLUMN status")

    # =====================
    # EP-02: VENDORS TABLE
    # =====================
    # Revert vendor_type enum
    op.execute("""
        ALTER TABLE vendors
        ADD COLUMN vendor_type_old ENUM(
            'property_manager', 'maintenance', 'cleaning', 'security', 'utilities', 'other'
        ) NOT NULL DEFAULT 'other'
        AFTER vendor_code
    """)
    op.execute("""
        UPDATE vendors SET vendor_type_old = CASE vendor_type
            WHEN 'individual' THEN 'other'
            WHEN 'company' THEN 'property_manager'
            ELSE 'other'
        END
    """)
    op.execute("DROP INDEX ix_vendors_type ON vendors")
    op.execute("ALTER TABLE vendors DROP COLUMN vendor_type")
    op.execute("""
        ALTER TABLE vendors
        CHANGE vendor_type_old vendor_type ENUM(
            'property_manager', 'maintenance', 'cleaning', 'security', 'utilities', 'other'
        ) NOT NULL DEFAULT 'other'
    """)
    op.execute("CREATE INDEX ix_vendors_type ON vendors (account_id, company_id, vendor_type)")

    op.execute("ALTER TABLE vendors DROP COLUMN active_leases_count")
    op.execute("""
        ALTER TABLE vendors
        ADD COLUMN mobile VARCHAR(50) NULL AFTER contact_phone
    """)
    op.execute("ALTER TABLE vendors DROP COLUMN address_line_2")
    op.execute("ALTER TABLE vendors CHANGE COLUMN address_line_1 address TEXT NULL")
    op.execute("ALTER TABLE vendors CHANGE COLUMN contact_email email VARCHAR(255) NULL")
    op.execute("ALTER TABLE vendors CHANGE COLUMN contact_phone phone VARCHAR(50) NULL")
    op.execute("ALTER TABLE vendors CHANGE COLUMN vendor_name name VARCHAR(255) NOT NULL")

    # =====================
    # EP-01: UNITS TABLE
    # =====================
    op.execute("ALTER TABLE units MODIFY COLUMN capacity INT NULL")
    op.execute("ALTER TABLE units DROP COLUMN sort_order")
    op.execute("ALTER TABLE units CHANGE COLUMN area_sqm area_sqft DECIMAL(10, 2) NULL")
    op.execute("ALTER TABLE units DROP COLUMN room_number")
    op.execute("ALTER TABLE units MODIFY COLUMN floor_number INT NULL")
    op.execute("ALTER TABLE units CHANGE COLUMN display_name name VARCHAR(255) NOT NULL")

    # =====================
    # EP-01: PROPERTIES TABLE
    # =====================
    op.execute("ALTER TABLE properties DROP COLUMN active_units_count")
    op.execute("ALTER TABLE properties DROP COLUMN total_units_count")
    op.execute("ALTER TABLE properties DROP COLUMN address_line_2")
    op.execute("ALTER TABLE properties CHANGE COLUMN address_line_1 address TEXT NULL")
    op.execute("ALTER TABLE properties CHANGE COLUMN property_name name VARCHAR(255) NOT NULL")

    # =====================
    # EP-01: UNIT_CATEGORIES TABLE
    # =====================
    op.execute("ALTER TABLE unit_categories DROP COLUMN max_depth")
    op.execute("ALTER TABLE unit_categories DROP COLUMN allowed_parent_categories")
    op.execute("ALTER TABLE unit_categories DROP COLUMN is_commercial")
    op.execute("ALTER TABLE unit_categories DROP COLUMN is_residential")
