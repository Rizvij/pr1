"""Initial schema for ProRyx Property Management System

Revision ID: 0001
Revises:
Create Date: 2024-12-08

Creates all tables for:
- Auth (accounts, companies, roles, users, refresh_tokens)
- Property Management (unit_categories, properties, units)
- Vendor Management (vendors, vendor_leases, vendor_lease_terms, vendor_lease_coverages)
- Tenant Management (document_types, tenants, tenant_contacts, tenant_documents)
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables."""

    # =====================
    # LOOKUP TABLES (no FKs)
    # =====================

    # accounts - top-level SaaS tenant
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )

    # roles - user roles
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # unit_categories - lookup for unit types
    op.create_table(
        "unit_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # document_types - lookup for KYC documents
    op.create_table(
        "document_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("applicable_to", sa.Enum("individual", "entity", name="tenanttype"), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # =====================
    # COMPANIES (FK to accounts)
    # =====================

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_companies_account", "companies", ["account_id"])

    # =====================
    # USERS (AccountScoped)
    # =====================

    op.create_table(
        "users",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("first_name", sa.String(120), nullable=False),
        sa.Column("last_name", sa.String(120), nullable=True),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("account_id", "company_id", "id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.UniqueConstraint("account_id", "company_id", "uuid", name="uq_users_acct_comp_uuid"),
    )
    op.create_index("ix_users_email", "users", ["account_id", "company_id", "email"], unique=True)
    op.create_index("ix_users_account_company", "users", ["account_id", "company_id"])
    op.create_index("ix_users_account_id", "users", ["account_id"])
    op.create_index("ix_users_company_id", "users", ["company_id"])
    op.create_index("ix_users_uuid", "users", ["uuid"])

    # =====================
    # REFRESH TOKENS
    # =====================

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_account_id", sa.Integer(), nullable=False),
        sa.Column("user_company_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_user", "refresh_tokens", ["user_account_id", "user_company_id", "user_id"])
    op.create_index("ix_refresh_tokens_hash", "refresh_tokens", ["token_hash"])

    # =====================
    # PROPERTIES (AccountScoped)
    # =====================

    op.create_table(
        "properties",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("property_code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("usage_type", sa.Enum("residential", "commercial", "mixed", name="propertyusagetype"), nullable=False, server_default="residential"),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("state", sa.String(120), nullable=True),
        sa.Column("country", sa.String(120), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("total_floors", sa.Integer(), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("status", sa.Enum("active", "inactive", "under_maintenance", name="propertystatus"), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("account_id", "company_id", "id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("account_id", "company_id", "uuid", name="uq_properties_acct_comp_uuid"),
    )
    op.create_index("ix_properties_code", "properties", ["account_id", "company_id", "property_code"], unique=True)
    op.create_index("ix_properties_status", "properties", ["account_id", "company_id", "status"])
    op.create_index("ix_properties_account_id", "properties", ["account_id"])
    op.create_index("ix_properties_company_id", "properties", ["company_id"])
    op.create_index("ix_properties_uuid", "properties", ["uuid"])

    # =====================
    # UNITS (AccountScoped, FK to properties, self)
    # =====================

    op.create_table(
        "units",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("parent_unit_id", sa.Integer(), nullable=True),
        sa.Column("unit_code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("floor_number", sa.Integer(), nullable=True),
        sa.Column("area_sqft", sa.Numeric(10, 2), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("is_leaf", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("status", sa.Enum("available", "occupied", "reserved", "under_maintenance", "inactive", name="unitstatus"), nullable=False, server_default="available"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("account_id", "company_id", "id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["unit_categories.id"]),
        sa.ForeignKeyConstraint(
            ["account_id", "company_id", "property_id"],
            ["properties.account_id", "properties.company_id", "properties.id"],
            ondelete="CASCADE",
        ),
        # Note: Self-referencing FK without ON DELETE (MySQL doesn't support SET NULL on NOT NULL columns)
        # Application must handle parent deletion by setting parent_unit_id = NULL first
        sa.UniqueConstraint("account_id", "company_id", "uuid", name="uq_units_acct_comp_uuid"),
    )
    op.create_index("ix_units_code", "units", ["account_id", "company_id", "property_id", "unit_code"], unique=True)
    op.create_index("ix_units_property", "units", ["account_id", "company_id", "property_id"])
    op.create_index("ix_units_parent", "units", ["account_id", "company_id", "parent_unit_id"])
    op.create_index("ix_units_status", "units", ["account_id", "company_id", "status"])
    op.create_index("ix_units_is_leaf", "units", ["account_id", "company_id", "is_leaf"])
    op.create_index("ix_units_account_id", "units", ["account_id"])
    op.create_index("ix_units_company_id", "units", ["company_id"])
    op.create_index("ix_units_uuid", "units", ["uuid"])

    # =====================
    # VENDORS (AccountScoped)
    # =====================

    op.create_table(
        "vendors",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("vendor_code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("vendor_type", sa.Enum("property_manager", "maintenance", "cleaning", "security", "utilities", "other", name="vendortype"), nullable=False, server_default="other"),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("mobile", sa.String(50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("country", sa.String(120), nullable=True),
        sa.Column("bank_name", sa.String(255), nullable=True),
        sa.Column("bank_account_name", sa.String(255), nullable=True),
        sa.Column("bank_account_number", sa.String(100), nullable=True),
        sa.Column("bank_iban", sa.String(50), nullable=True),
        sa.Column("bank_swift", sa.String(20), nullable=True),
        sa.Column("tax_registration_number", sa.String(100), nullable=True),
        sa.Column("status", sa.Enum("active", "inactive", "suspended", name="vendorstatus"), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("account_id", "company_id", "id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("account_id", "company_id", "uuid", name="uq_vendors_acct_comp_uuid"),
    )
    op.create_index("ix_vendors_code", "vendors", ["account_id", "company_id", "vendor_code"], unique=True)
    op.create_index("ix_vendors_type", "vendors", ["account_id", "company_id", "vendor_type"])
    op.create_index("ix_vendors_status", "vendors", ["account_id", "company_id", "status"])
    op.create_index("ix_vendors_account_id", "vendors", ["account_id"])
    op.create_index("ix_vendors_company_id", "vendors", ["company_id"])
    op.create_index("ix_vendors_uuid", "vendors", ["uuid"])

    # =====================
    # VENDOR LEASES (AccountScoped, FK to vendors)
    # =====================

    op.create_table(
        "vendor_leases",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("lease_code", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("rent_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="AED"),
        sa.Column("billing_cycle", sa.Enum("monthly", "quarterly", "semi_annual", "annual", name="billingcycle"), nullable=False, server_default="monthly"),
        sa.Column("security_deposit", sa.Numeric(15, 2), nullable=True),
        sa.Column("status", sa.Enum("draft", "active", "expired", "terminated", "renewed", name="leasestatus"), nullable=False, server_default="draft"),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("termination_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("account_id", "company_id", "id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["account_id", "company_id", "vendor_id"],
            ["vendors.account_id", "vendors.company_id", "vendors.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("account_id", "company_id", "uuid", name="uq_vendor_leases_acct_comp_uuid"),
    )
    op.create_index("ix_vendor_leases_code", "vendor_leases", ["account_id", "company_id", "lease_code"], unique=True)
    op.create_index("ix_vendor_leases_vendor", "vendor_leases", ["account_id", "company_id", "vendor_id"])
    op.create_index("ix_vendor_leases_status", "vendor_leases", ["account_id", "company_id", "status"])
    op.create_index("ix_vendor_leases_dates", "vendor_leases", ["account_id", "company_id", "start_date", "end_date"])
    op.create_index("ix_vendor_leases_account_id", "vendor_leases", ["account_id"])
    op.create_index("ix_vendor_leases_company_id", "vendor_leases", ["company_id"])
    op.create_index("ix_vendor_leases_uuid", "vendor_leases", ["uuid"])

    # =====================
    # VENDOR LEASE TERMS (AccountScoped, FK to vendor_leases)
    # =====================

    op.create_table(
        "vendor_lease_terms",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("lease_id", sa.Integer(), nullable=False),
        sa.Column("term_number", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("rent_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("account_id", "company_id", "id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["account_id", "company_id", "lease_id"],
            ["vendor_leases.account_id", "vendor_leases.company_id", "vendor_leases.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("account_id", "company_id", "uuid", name="uq_vendor_lease_terms_acct_comp_uuid"),
    )
    op.create_index("ix_vendor_lease_terms_lease", "vendor_lease_terms", ["account_id", "company_id", "lease_id"])
    op.create_index("ix_vendor_lease_terms_unique", "vendor_lease_terms", ["account_id", "company_id", "lease_id", "term_number"], unique=True)
    op.create_index("ix_vendor_lease_terms_account_id", "vendor_lease_terms", ["account_id"])
    op.create_index("ix_vendor_lease_terms_company_id", "vendor_lease_terms", ["company_id"])
    op.create_index("ix_vendor_lease_terms_uuid", "vendor_lease_terms", ["uuid"])

    # =====================
    # VENDOR LEASE COVERAGES (AccountScoped, FK to vendor_leases, properties, units)
    # =====================

    op.create_table(
        "vendor_lease_coverages",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("lease_id", sa.Integer(), nullable=False),
        sa.Column("scope_type", sa.Enum("property", "unit", name="coveragescope"), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=True),
        sa.Column("unit_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("account_id", "company_id", "id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["account_id", "company_id", "lease_id"],
            ["vendor_leases.account_id", "vendor_leases.company_id", "vendor_leases.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "company_id", "property_id"],
            ["properties.account_id", "properties.company_id", "properties.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "company_id", "unit_id"],
            ["units.account_id", "units.company_id", "units.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("account_id", "company_id", "uuid", name="uq_vendor_lease_coverages_acct_comp_uuid"),
    )
    op.create_index("ix_vendor_lease_coverages_lease", "vendor_lease_coverages", ["account_id", "company_id", "lease_id"])
    op.create_index("ix_vendor_lease_coverages_property", "vendor_lease_coverages", ["account_id", "company_id", "property_id"])
    op.create_index("ix_vendor_lease_coverages_unit", "vendor_lease_coverages", ["account_id", "company_id", "unit_id"])
    op.create_index("ix_vendor_lease_coverages_account_id", "vendor_lease_coverages", ["account_id"])
    op.create_index("ix_vendor_lease_coverages_company_id", "vendor_lease_coverages", ["company_id"])
    op.create_index("ix_vendor_lease_coverages_uuid", "vendor_lease_coverages", ["uuid"])

    # =====================
    # TENANTS (AccountScoped)
    # =====================

    op.create_table(
        "tenants",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("tenant_code", sa.String(50), nullable=False),
        sa.Column("tenant_type", sa.Enum("individual", "entity", name="tenanttype"), nullable=False, server_default="individual"),
        # Individual fields
        sa.Column("first_name", sa.String(120), nullable=True),
        sa.Column("last_name", sa.String(120), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("nationality", sa.String(100), nullable=True),
        sa.Column("passport_number", sa.String(50), nullable=True),
        sa.Column("emirates_id", sa.String(50), nullable=True),
        # Entity fields
        sa.Column("entity_name", sa.String(255), nullable=True),
        sa.Column("trade_license_number", sa.String(100), nullable=True),
        sa.Column("registration_number", sa.String(100), nullable=True),
        # Contact
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("mobile", sa.String(50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("country", sa.String(120), nullable=True),
        # KYC
        sa.Column("kyc_status", sa.Enum("pending", "in_progress", "verified", "rejected", "expired", name="kycstatus"), nullable=False, server_default="pending"),
        sa.Column("kyc_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("kyc_verified_by_id", sa.Integer(), nullable=True),
        # Status
        sa.Column("status", sa.Enum("active", "inactive", "blacklisted", name="tenantstatus"), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("account_id", "company_id", "id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("account_id", "company_id", "uuid", name="uq_tenants_acct_comp_uuid"),
    )
    op.create_index("ix_tenants_code", "tenants", ["account_id", "company_id", "tenant_code"], unique=True)
    op.create_index("ix_tenants_type", "tenants", ["account_id", "company_id", "tenant_type"])
    op.create_index("ix_tenants_status", "tenants", ["account_id", "company_id", "status"])
    op.create_index("ix_tenants_kyc_status", "tenants", ["account_id", "company_id", "kyc_status"])
    op.create_index("ix_tenants_passport", "tenants", ["account_id", "company_id", "passport_number"])
    op.create_index("ix_tenants_emirates_id", "tenants", ["account_id", "company_id", "emirates_id"])
    op.create_index("ix_tenants_account_id", "tenants", ["account_id"])
    op.create_index("ix_tenants_company_id", "tenants", ["company_id"])
    op.create_index("ix_tenants_uuid", "tenants", ["uuid"])

    # =====================
    # TENANT CONTACTS (AccountScoped, FK to tenants)
    # =====================

    op.create_table(
        "tenant_contacts",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(120), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("mobile", sa.String(50), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("account_id", "company_id", "id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["account_id", "company_id", "tenant_id"],
            ["tenants.account_id", "tenants.company_id", "tenants.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("account_id", "company_id", "uuid", name="uq_tenant_contacts_acct_comp_uuid"),
    )
    op.create_index("ix_tenant_contacts_tenant", "tenant_contacts", ["account_id", "company_id", "tenant_id"])
    op.create_index("ix_tenant_contacts_primary", "tenant_contacts", ["account_id", "company_id", "tenant_id", "is_primary"])
    op.create_index("ix_tenant_contacts_account_id", "tenant_contacts", ["account_id"])
    op.create_index("ix_tenant_contacts_company_id", "tenant_contacts", ["company_id"])
    op.create_index("ix_tenant_contacts_uuid", "tenant_contacts", ["uuid"])

    # =====================
    # TENANT DOCUMENTS (AccountScoped, FK to tenants, document_types)
    # =====================

    op.create_table(
        "tenant_documents",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("document_type_id", sa.Integer(), nullable=False),
        sa.Column("document_number", sa.String(100), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("issuing_authority", sa.String(255), nullable=True),
        sa.Column("issuing_country", sa.String(120), nullable=True),
        # File storage
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        # Verification
        sa.Column("verification_status", sa.Enum("pending", "verified", "rejected", "expired", name="documentverificationstatus"), nullable=False, server_default="pending"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by_id", sa.Integer(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("account_id", "company_id", "id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["account_id", "company_id", "tenant_id"],
            ["tenants.account_id", "tenants.company_id", "tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"]),
        sa.UniqueConstraint("account_id", "company_id", "uuid", name="uq_tenant_documents_acct_comp_uuid"),
    )
    op.create_index("ix_tenant_documents_tenant", "tenant_documents", ["account_id", "company_id", "tenant_id"])
    op.create_index("ix_tenant_documents_type", "tenant_documents", ["account_id", "company_id", "tenant_id", "document_type_id"])
    op.create_index("ix_tenant_documents_status", "tenant_documents", ["account_id", "company_id", "verification_status"])
    op.create_index("ix_tenant_documents_expiry", "tenant_documents", ["account_id", "company_id", "expiry_date"])
    op.create_index("ix_tenant_documents_account_id", "tenant_documents", ["account_id"])
    op.create_index("ix_tenant_documents_company_id", "tenant_documents", ["company_id"])
    op.create_index("ix_tenant_documents_uuid", "tenant_documents", ["uuid"])

    # =====================
    # SEED DATA
    # =====================

    # Insert default roles
    op.execute("""
        INSERT INTO roles (slug, name, description) VALUES
        ('admin', 'Administrator', 'Full system access'),
        ('manager', 'Manager', 'Manage properties, vendors, and tenants'),
        ('leasing', 'Leasing Agent', 'Manage leases and tenant onboarding'),
        ('operations', 'Operations', 'Property and unit operations'),
        ('finance', 'Finance', 'Financial operations and reporting'),
        ('viewer', 'Viewer', 'Read-only access')
    """)

    # Insert default unit categories
    op.execute("""
        INSERT INTO unit_categories (code, name, description, is_active) VALUES
        ('APARTMENT', 'Apartment', 'Full apartment unit', 1),
        ('BEDSPACE', 'Bedspace', 'Single bed space in shared accommodation', 1),
        ('STUDIO', 'Studio', 'Studio apartment', 1),
        ('ROOM', 'Room', 'Individual room', 1),
        ('SHOP', 'Shop', 'Retail shop unit', 1),
        ('OFFICE', 'Office', 'Office space', 1),
        ('WAREHOUSE', 'Warehouse', 'Storage/warehouse space', 1),
        ('PARKING', 'Parking', 'Parking space', 1),
        ('FLOOR', 'Floor', 'Building floor (container unit)', 1),
        ('BUILDING', 'Building', 'Building within a property (container unit)', 1)
    """)

    # Insert default document types
    op.execute("""
        INSERT INTO document_types (code, name, description, applicable_to, is_mandatory, is_active) VALUES
        ('PASSPORT', 'Passport', 'Valid passport document', 'individual', 1, 1),
        ('EMIRATES_ID', 'Emirates ID', 'UAE Emirates ID card', 'individual', 1, 1),
        ('VISA', 'Residence Visa', 'UAE residence visa', 'individual', 0, 1),
        ('PHOTO', 'Passport Photo', 'Recent passport-sized photograph', 'individual', 0, 1),
        ('TRADE_LICENSE', 'Trade License', 'Business trade license', 'entity', 1, 1),
        ('MEMORANDUM', 'Memorandum of Association', 'Company memorandum', 'entity', 0, 1),
        ('POWER_OF_ATTORNEY', 'Power of Attorney', 'Authorized signatory POA', 'entity', 0, 1),
        ('VAT_CERTIFICATE', 'VAT Certificate', 'VAT registration certificate', 'entity', 0, 1),
        ('TENANCY_CONTRACT', 'Previous Tenancy Contract', 'Previous rental agreement', NULL, 0, 1),
        ('BANK_STATEMENT', 'Bank Statement', 'Recent bank statement', NULL, 0, 1),
        ('SALARY_CERTIFICATE', 'Salary Certificate', 'Employment salary certificate', 'individual', 0, 1),
        ('EMPLOYMENT_CONTRACT', 'Employment Contract', 'Employment agreement', 'individual', 0, 1)
    """)


def downgrade() -> None:
    """Drop all tables in reverse order."""

    # Drop tenant management tables
    op.drop_table("tenant_documents")
    op.drop_table("tenant_contacts")
    op.drop_table("tenants")

    # Drop vendor management tables
    op.drop_table("vendor_lease_coverages")
    op.drop_table("vendor_lease_terms")
    op.drop_table("vendor_leases")
    op.drop_table("vendors")

    # Drop property management tables
    op.drop_table("units")
    op.drop_table("properties")

    # Drop auth tables
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("companies")

    # Drop lookup tables
    op.drop_table("document_types")
    op.drop_table("unit_categories")
    op.drop_table("roles")
    op.drop_table("accounts")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS documentverificationstatus")
    op.execute("DROP TYPE IF EXISTS tenantstatus")
    op.execute("DROP TYPE IF EXISTS kycstatus")
    op.execute("DROP TYPE IF EXISTS tenanttype")
    op.execute("DROP TYPE IF EXISTS coveragescope")
    op.execute("DROP TYPE IF EXISTS leasestatus")
    op.execute("DROP TYPE IF EXISTS billingcycle")
    op.execute("DROP TYPE IF EXISTS vendorstatus")
    op.execute("DROP TYPE IF EXISTS vendortype")
    op.execute("DROP TYPE IF EXISTS unitstatus")
    op.execute("DROP TYPE IF EXISTS propertystatus")
    op.execute("DROP TYPE IF EXISTS propertyusagetype")
