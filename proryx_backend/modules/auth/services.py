"""Authentication business logic services."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions import (
    AuthenticationError,
    NotFoundError,
    ValidationError,
)
from . import crud
from .jwt_service import (
    create_access_token,
    create_refresh_token,
    get_token_expiry_seconds,
    hash_refresh_token,
)
from .models import User
from .password_service import verify_password
from .schemas import TokenResponse

# Account lockout settings
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
    remember_me: bool = False,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[User, TokenResponse]:
    """Authenticate user and return tokens.

    Args:
        db: Database session
        email: User's email
        password: User's password
        remember_me: Whether to extend refresh token expiry
        user_agent: Client user agent string
        ip_address: Client IP address

    Returns:
        Tuple of (User, TokenResponse)

    Raises:
        AuthenticationError: If authentication fails
    """
    # Find user by email (global search for login)
    user = await crud.get_user_by_email_global(db, email)
    if not user:
        raise AuthenticationError("Invalid email or password")

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        remaining = (user.locked_until - datetime.now(timezone.utc)).seconds // 60
        raise AuthenticationError(
            f"Account is locked. Try again in {remaining + 1} minutes."
        )

    # Check if user is active
    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    # Verify password
    if not verify_password(password, user.password_hash):
        await crud.increment_failed_login(db, user)

        # Lock account if too many failed attempts
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            lock_until = datetime.now(timezone.utc) + timedelta(
                minutes=LOCKOUT_DURATION_MINUTES
            )
            await crud.lock_user(db, user, lock_until)
            raise AuthenticationError(
                f"Account locked due to too many failed attempts. "
                f"Try again in {LOCKOUT_DURATION_MINUTES} minutes."
            )

        remaining_attempts = MAX_FAILED_ATTEMPTS - user.failed_login_attempts
        raise AuthenticationError(
            f"Invalid email or password. {remaining_attempts} attempts remaining."
        )

    # Update last login
    await crud.update_user_last_login(db, user)

    # Generate tokens
    access_token = create_access_token(
        user_id=user.id,
        account_id=user.account_id,
        company_id=user.company_id,
        email=user.email,
        role_slug=user.role.slug,
    )

    refresh_token, refresh_expires = create_refresh_token(remember_me)

    # Store refresh token
    await crud.create_refresh_token(
        db=db,
        user=user,
        token=refresh_token,
        expires_at=refresh_expires,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    await db.commit()

    return user, TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=get_token_expiry_seconds(remember_me),
    )


async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenResponse:
    """Refresh access token using refresh token.

    Args:
        db: Database session
        refresh_token: The refresh token string
        user_agent: Client user agent string
        ip_address: Client IP address

    Returns:
        New TokenResponse with fresh tokens

    Raises:
        AuthenticationError: If refresh token is invalid or expired
    """
    # Find refresh token
    token_hash = hash_refresh_token(refresh_token)
    stored_token = await crud.get_refresh_token_by_hash(db, token_hash)

    if not stored_token:
        raise AuthenticationError("Invalid refresh token")

    if stored_token.is_revoked:
        raise AuthenticationError("Refresh token has been revoked")

    if stored_token.is_expired:
        raise AuthenticationError("Refresh token has expired")

    # Get user
    user = await crud.get_user_by_id(
        db,
        user_id=stored_token.user_id,
        account_id=stored_token.user_account_id,
        company_id=stored_token.user_company_id,
    )

    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    # Revoke old refresh token
    await crud.revoke_refresh_token(db, stored_token)

    # Generate new tokens
    access_token = create_access_token(
        user_id=user.id,
        account_id=user.account_id,
        company_id=user.company_id,
        email=user.email,
        role_slug=user.role.slug,
    )

    new_refresh_token, refresh_expires = create_refresh_token(remember_me=False)

    # Store new refresh token
    await crud.create_refresh_token(
        db=db,
        user=user,
        token=new_refresh_token,
        expires_at=refresh_expires,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=get_token_expiry_seconds(),
    )


async def logout_user(
    db: AsyncSession,
    account_id: int,
    company_id: int,
    user_id: int,
) -> int:
    """Logout user by revoking all their refresh tokens.

    Args:
        db: Database session
        account_id: User's account ID
        company_id: User's company ID
        user_id: User's ID

    Returns:
        Number of tokens revoked
    """
    count = await crud.revoke_all_user_tokens(db, account_id, company_id, user_id)
    await db.commit()
    return count


async def change_password(
    db: AsyncSession,
    user_id: int,
    account_id: int,
    company_id: int,
    current_password: str,
    new_password: str,
) -> None:
    """Change user's password.

    Args:
        db: Database session
        user_id: User's ID
        account_id: User's account ID
        company_id: User's company ID
        current_password: Current password for verification
        new_password: New password to set

    Raises:
        NotFoundError: If user not found
        ValidationError: If current password is incorrect
    """
    user = await crud.get_user_by_id(db, user_id, account_id, company_id)
    if not user:
        raise NotFoundError("User not found")

    if not verify_password(current_password, user.password_hash):
        raise ValidationError("Current password is incorrect")

    await crud.update_user_password(db, user, new_password)

    # Revoke all existing refresh tokens for security
    await crud.revoke_all_user_tokens(db, account_id, company_id, user_id)

    await db.commit()


async def create_initial_admin(
    db: AsyncSession,
    account_name: str,
    company_name: str,
    admin_email: str,
    admin_password: str,
    admin_first_name: str,
    admin_last_name: str | None = None,
) -> User:
    """Create initial account, company, and admin user.

    This is used for seeding a fresh database with the first admin user.

    Args:
        db: Database session
        account_name: Name for the account
        company_name: Name for the company
        admin_email: Admin user's email
        admin_password: Admin user's password
        admin_first_name: Admin's first name
        admin_last_name: Admin's last name (optional)

    Returns:
        Created admin User

    Raises:
        ValidationError: If account/user already exists
    """
    import uuid

    from sqlalchemy import select, text

    from .models import Account, Company, Role, RoleSlug
    from .password_service import hash_password

    # Check if any accounts exist
    result = await db.execute(text("SELECT id FROM accounts LIMIT 1"))
    if result.scalar():
        raise ValidationError("Database already has accounts. Cannot seed.")

    # Get admin role
    result = await db.execute(select(Role).where(Role.slug == RoleSlug.ADMIN.value))
    admin_role = result.scalar_one_or_none()
    if not admin_role:
        raise ValidationError("Admin role not found. Run migrations first.")

    # Create account
    account = Account(
        uuid=str(uuid.uuid4()),
        name=account_name,
        is_active=True,
    )
    db.add(account)
    await db.flush()

    # Create company
    company = Company(
        uuid=str(uuid.uuid4()),
        account_id=account.id,
        name=company_name,
        is_active=True,
    )
    db.add(company)
    await db.flush()

    # Create admin user
    user = User(
        account_id=account.id,
        company_id=company.id,
        id=1,  # First user in tenant
        uuid=uuid.uuid4(),
        email=admin_email,
        password_hash=hash_password(admin_password),
        first_name=admin_first_name,
        last_name=admin_last_name,
        role_id=admin_role.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()

    return user
