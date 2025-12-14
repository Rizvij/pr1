"""CRUD operations for authentication module."""

from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .jwt_service import hash_refresh_token
from .models import Account, Company, RefreshToken, Role, User
from .password_service import hash_password

# ----- Account CRUD -----


async def get_account_by_id(db: AsyncSession, account_id: int) -> Account | None:
    """Get an account by ID."""
    result = await db.execute(select(Account).where(Account.id == account_id))
    return result.scalar_one_or_none()


async def get_account_by_uuid(db: AsyncSession, uuid: str) -> Account | None:
    """Get an account by UUID."""
    result = await db.execute(select(Account).where(Account.uuid == uuid))
    return result.scalar_one_or_none()


async def create_account(db: AsyncSession, name: str) -> Account:
    """Create a new account."""
    import uuid

    account = Account(uuid=str(uuid.uuid4()), name=name, is_active=True)
    db.add(account)
    await db.flush()
    return account


# ----- Company CRUD -----


async def get_company_by_id(
    db: AsyncSession, company_id: int, account_id: int | None = None
) -> Company | None:
    """Get a company by ID, optionally filtered by account."""
    query = select(Company).where(Company.id == company_id)
    if account_id:
        query = query.where(Company.account_id == account_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_companies_by_account(db: AsyncSession, account_id: int) -> list[Company]:
    """Get all companies for an account."""
    result = await db.execute(select(Company).where(Company.account_id == account_id))
    return list(result.scalars().all())


async def create_company(db: AsyncSession, name: str, account_id: int) -> Company:
    """Create a new company."""
    import uuid

    company = Company(
        uuid=str(uuid.uuid4()), account_id=account_id, name=name, is_active=True
    )
    db.add(company)
    await db.flush()
    return company


# ----- Role CRUD -----


async def get_role_by_id(db: AsyncSession, role_id: int) -> Role | None:
    """Get a role by ID."""
    result = await db.execute(select(Role).where(Role.id == role_id))
    return result.scalar_one_or_none()


async def get_role_by_slug(db: AsyncSession, slug: str) -> Role | None:
    """Get a role by slug."""
    result = await db.execute(select(Role).where(Role.slug == slug))
    return result.scalar_one_or_none()


async def get_all_roles(db: AsyncSession) -> list[Role]:
    """Get all roles."""
    result = await db.execute(select(Role))
    return list(result.scalars().all())


async def create_role(
    db: AsyncSession, slug: str, name: str, description: str | None = None
) -> Role:
    """Create a new role."""
    role = Role(slug=slug, name=name, description=description)
    db.add(role)
    await db.flush()
    return role


# ----- User CRUD -----


async def get_user_by_id(
    db: AsyncSession, user_id: int, account_id: int, company_id: int
) -> User | None:
    """Get a user by ID within tenant scope."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .where(
            and_(
                User.id == user_id,
                User.account_id == account_id,
                User.company_id == company_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_email(
    db: AsyncSession, email: str, account_id: int, company_id: int
) -> User | None:
    """Get a user by email within tenant scope."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .where(
            and_(
                User.email == email,
                User.account_id == account_id,
                User.company_id == company_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_email_global(db: AsyncSession, email: str) -> User | None:
    """Get a user by email across all tenants (for login)."""
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_users_by_tenant(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    skip: int = 0,
    limit: int = 100,
    is_active: bool | None = None,
) -> list[User]:
    """Get all users within tenant scope."""
    query = (
        select(User)
        .options(selectinload(User.role))
        .where(and_(User.account_id == account_id, User.company_id == company_id))
    )
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_user(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    email: str,
    password: str,
    first_name: str,
    last_name: str | None,
    role_id: int,
) -> User:
    """Create a new user."""
    import uuid

    # Get next ID for this tenant
    result = await db.execute(
        select(User.id)
        .where(and_(User.account_id == account_id, User.company_id == company_id))
        .order_by(User.id.desc())
        .limit(1)
    )
    max_id = result.scalar_one_or_none()
    next_id = (max_id or 0) + 1

    user = User(
        account_id=account_id,
        company_id=company_id,
        id=next_id,
        uuid=str(uuid.uuid4()),
        email=email,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        role_id=role_id,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def update_user_last_login(db: AsyncSession, user: User) -> None:
    """Update user's last login timestamp."""
    user.last_login = datetime.now(timezone.utc)
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.flush()


async def increment_failed_login(db: AsyncSession, user: User) -> None:
    """Increment failed login attempts."""
    user.failed_login_attempts += 1
    await db.flush()


async def lock_user(db: AsyncSession, user: User, until: datetime) -> None:
    """Lock user until specified time."""
    user.locked_until = until
    await db.flush()


async def update_user(
    db: AsyncSession,
    user: User,
    first_name: str | None = None,
    last_name: str | None = None,
    role_id: int | None = None,
    is_active: bool | None = None,
) -> User:
    """Update user fields."""
    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name
    if role_id is not None:
        user.role_id = role_id
    if is_active is not None:
        user.is_active = is_active
    await db.flush()
    return user


async def update_user_password(db: AsyncSession, user: User, new_password: str) -> None:
    """Update user's password."""
    user.password_hash = hash_password(new_password)
    await db.flush()


# ----- Refresh Token CRUD -----


async def create_refresh_token(
    db: AsyncSession,
    user: User,
    token: str,
    expires_at: datetime,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> RefreshToken:
    """Create a new refresh token."""
    refresh_token = RefreshToken(
        user_account_id=user.account_id,
        user_company_id=user.company_id,
        user_id=user.id,
        token_hash=hash_refresh_token(token),
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(refresh_token)
    await db.flush()
    return refresh_token


async def get_refresh_token_by_hash(
    db: AsyncSession, token_hash: str
) -> RefreshToken | None:
    """Get a refresh token by its hash."""
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


async def revoke_refresh_token(db: AsyncSession, token: RefreshToken) -> None:
    """Revoke a refresh token."""
    token.revoked_at = datetime.now(timezone.utc)
    await db.flush()


async def revoke_all_user_tokens(
    db: AsyncSession, account_id: int, company_id: int, user_id: int
) -> int:
    """Revoke all refresh tokens for a user. Returns count of revoked tokens."""
    result = await db.execute(
        select(RefreshToken).where(
            and_(
                RefreshToken.user_account_id == account_id,
                RefreshToken.user_company_id == company_id,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
    )
    tokens = result.scalars().all()
    now = datetime.now(timezone.utc)
    for token in tokens:
        token.revoked_at = now
    await db.flush()
    return len(tokens)
