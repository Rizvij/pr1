# System Architecture Overview

## Introduction

ProRyx is a property management system for short-term rentals, built with a FastAPI backend and React frontend. The system implements two-level multi-tenancy for complete data isolation between organizations.

---

## Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **FastAPI** | Async Python web framework |
| **SQLAlchemy 2.0** | Async ORM with MySQL |
| **Pydantic** | Data validation and serialization |
| **JWT** | Authentication tokens |
| **bcrypt** | Password hashing |
| **Alembic** | Database migrations |

### Frontend
| Technology | Purpose |
|------------|---------|
| **React 18** | UI framework |
| **Vite** | Build tool and dev server |
| **TypeScript** | Type safety |
| **TailwindCSS** | Utility-first styling |
| **TanStack Query** | Server state management |
| **Zustand** | Client state management |
| **React Router** | Client-side routing |

### Database
- **MySQL 8.0** with async driver (asyncmy)

---

## Multi-Tenancy Model

ProRyx implements **two-level multi-tenancy**:

### Level 1: Account
- Top-level SaaS tenant (organization)
- Represents a distinct business entity
- Complete data isolation from other accounts

### Level 2: Company
- Second-level tenant within an account
- Allows organizations to have multiple business units
- Data isolated within the parent account

### Implementation

All tenant-scoped models inherit from `AccountScoped`:

```python
class AccountScoped:
    account_id: Mapped[int]  # Primary key part 1
    company_id: Mapped[int]  # Primary key part 2
    id: Mapped[int]          # Primary key part 3
    uuid: Mapped[str]        # External reference (API-facing)
```

### Data Flow

```
Request → JWT Token → Extract (account_id, company_id) → Filter all queries
```

All CRUD operations automatically filter by both `account_id` AND `company_id`, ensuring complete tenant isolation.

---

## Backend Architecture

### Directory Structure

```
proryx_backend/
├── main.py              # Application entry point
├── config.py            # Settings management (YAML-based)
├── database.py          # Database connection & AccountScoped mixin
├── core/
│   ├── base_crud.py     # Generic CRUD with tenant filtering
│   ├── exceptions.py    # Custom exception classes
│   ├── pagination.py    # Pagination utilities
│   ├── utils.py         # Helper functions
│   └── logging/         # Structured logging
└── modules/
    ├── auth/            # Authentication & authorization
    ├── commons/         # Shared schemas
    ├── property_management/  # EP-01: Properties & Units
    ├── vendor_management/    # EP-02: Vendors & Leases
    └── tenant_management/    # EP-03: Tenants & KYC
```

### Module Structure

Each business module follows a consistent pattern:

```
modules/feature_name/
├── __init__.py      # Public exports (router, models)
├── models.py        # SQLAlchemy ORM models
├── schemas.py       # Pydantic request/response schemas
├── crud.py          # Database operations (create, read, update, delete)
├── services.py      # Business logic layer
└── routers.py       # API endpoint definitions
```

### Request Flow

```
HTTP Request
    ↓
FastAPI Router (routers.py)
    ↓
Dependency Injection (get_current_user, get_db)
    ↓
Service Layer (services.py) - Business logic
    ↓
CRUD Layer (crud.py) - Database operations
    ↓
SQLAlchemy Models (models.py)
    ↓
MySQL Database
```

---

## Frontend Architecture

### Directory Structure

```
ui/customer-app/
├── src/
│   ├── main.tsx         # Application entry
│   ├── App.tsx          # Router configuration
│   ├── api/             # TanStack Query hooks
│   │   └── auth.ts      # Authentication API calls
│   ├── components/      # Reusable UI components
│   │   └── layouts/     # Page layouts
│   ├── pages/           # Route-based page components
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── properties/
│   │   ├── vendors/
│   │   └── tenants/
│   ├── stores/          # Zustand state stores
│   │   └── authStore.ts # Authentication state
│   ├── lib/             # Utilities
│   │   ├── api-client.ts    # Axios instance with interceptors
│   │   ├── queryClient.ts   # TanStack Query config
│   │   └── utils.ts         # Helper functions
│   └── types/           # TypeScript type definitions
└── index.html
```

### State Management

| State Type | Technology | Example |
|------------|------------|---------|
| Server state | TanStack Query | API data (properties, tenants) |
| Client state | Zustand | Auth tokens, UI state |
| Form state | React state | Form inputs |

### API Client

The `api-client.ts` configures:
- Base URL (`/api`)
- JWT token injection via interceptors
- Automatic token refresh on 401
- Error handling

---

## Functional Modules

### EP-01: Property & Unit Management

Manages properties and their hierarchical units.

**Models:**
- `Property` - Real estate property
- `Unit` - Space within a property (apartment, bedspace, shop)
- `UnitCategory` - Unit type definitions

**Unit Hierarchy:**
```
Property
└── Building (Unit)
    └── Floor (Unit)
        └── Apartment (Unit)
            └── Bedspace (Unit)
```

**API Endpoints:**
- `GET/POST /api/properties`
- `GET/PUT/DELETE /api/properties/{uuid}`
- `GET/POST /api/units`
- `GET /api/properties/{uuid}/units/hierarchy`

---

### EP-02: Vendor & Lease Management

Manages property vendors and lease agreements.

**Models:**
- `Vendor` - Property management vendor
- `VendorLease` - Lease agreement between vendor and property
- `VendorLeaseTerm` - Lease terms (payment, duration)
- `VendorLeaseCoverage` - Units covered by lease

**Lease Lifecycle:**
```
DRAFT → ACTIVE → TERMINATED
              → EXPIRED
```

**API Endpoints:**
- `GET/POST /api/vendors`
- `GET/PUT/DELETE /api/vendors/{uuid}`
- `GET/POST /api/vendor-leases`
- `POST /api/vendor-leases/{uuid}/activate`
- `POST /api/vendor-leases/{uuid}/terminate`

---

### EP-03: Tenant Management & KYC

Manages tenants with KYC document verification.

**Models:**
- `Tenant` - Individual or entity tenant
- `TenantContact` - Contact information
- `TenantDocument` - KYC documents
- `DocumentType` - Document type definitions

**Tenant Types:**
- `INDIVIDUAL` - Personal tenant
- `ENTITY` - Company/organization tenant

**KYC Status Flow:**
```
PENDING → UNDER_REVIEW → VERIFIED
                      → REJECTED
```

**API Endpoints:**
- `GET/POST /api/tenants`
- `POST /api/tenants/individual`
- `POST /api/tenants/entity`
- `PUT /api/tenants/{uuid}/kyc-status`
- `POST /api/tenants/{uuid}/documents`
- `POST /api/tenants/{uuid}/documents/{doc_uuid}/verify`

---

## Authentication & Security

### JWT Token Flow

```
Login Request (email, password)
    ↓
Validate credentials
    ↓
Generate tokens:
  - Access token (30 min)
  - Refresh token (7 days, or 30 with remember_me)
    ↓
Client stores tokens
    ↓
Subsequent requests include: Authorization: Bearer <access_token>
    ↓
On 401: Use refresh token to get new access token
```

### Security Features

| Feature | Implementation |
|---------|----------------|
| Password hashing | bcrypt |
| Token algorithm | HS256 |
| Account lockout | 5 failed attempts → 30 min lockout |
| Token refresh | Automatic via frontend interceptor |

### Protected Routes

All endpoints except `/api/auth/login` require authentication.

The `get_current_user` dependency:
1. Extracts JWT from Authorization header
2. Validates token signature and expiry
3. Loads user with account_id and company_id
4. Injects into route handlers

---

## Database Schema

### Core Tables

```
accounts
├── id (PK)
├── name
└── ...

companies
├── account_id (PK, FK)
├── id (PK)
├── name
└── ...

users
├── account_id (PK, FK)
├── company_id (PK, FK)
├── id (PK)
├── email
├── password_hash
└── ...
```

### Composite Primary Keys

All tenant-scoped tables use composite primary keys:
```sql
PRIMARY KEY (account_id, company_id, id)
```

This ensures:
- Data isolation at database level
- Efficient queries within tenant scope
- No ID collisions across tenants

---

## Configuration

### YAML-Based Settings

Configuration loaded from `resources/config/`:

```yaml
# local.yaml
app_env: "development"
database_url: "mysql+asyncmy://user:pass@localhost:3306/db_proryx"
jwt_secret_key: "dev-secret"
cors_origins:
  - "http://localhost:3000"
```

### Environment Variable Override

Production configs use environment variables:
```yaml
database_url: "mysql+asyncmy://${DB_USER}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}"
jwt_secret_key: "${JWT_SECRET_KEY}"
```

---

## Future Modules

- **EP-04:** Tenant Contracts
- **EP-05:** Billing & Invoicing
- **TOTP 2FA:** Time-based one-time passwords
- **Advanced RBAC:** Role-based access control
- **File Uploads:** KYC document storage
