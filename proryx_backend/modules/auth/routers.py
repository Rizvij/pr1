"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ..commons import BaseResponse
from . import crud, services
from .dependencies import CurrentUser
from .schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RoleResponse,
    TokenResponse,
    UserWithContext,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_client_info(request: Request) -> tuple[str | None, str | None]:
    """Extract client info from request."""
    user_agent = request.headers.get("user-agent")
    # Get IP from X-Forwarded-For header or fall back to client host
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else None
    return user_agent, ip_address


@router.post("/login", response_model=BaseResponse[TokenResponse])
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Authenticate user and return access/refresh tokens."""
    user_agent, ip_address = get_client_info(request)

    user, tokens = await services.authenticate_user(
        db=db,
        email=login_data.email,
        password=login_data.password,
        remember_me=login_data.remember_me,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    return BaseResponse(
        success=True,
        message=f"Welcome back, {user.first_name}!",
        data=tokens,
    )


@router.post("/refresh", response_model=BaseResponse[TokenResponse])
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Refresh access token using refresh token."""
    user_agent, ip_address = get_client_info(request)

    tokens = await services.refresh_access_token(
        db=db,
        refresh_token=refresh_data.refresh_token,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    return BaseResponse(
        success=True,
        message="Token refreshed successfully",
        data=tokens,
    )


@router.post("/logout", response_model=BaseResponse[None])
async def logout(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Logout user by revoking all refresh tokens."""
    count = await services.logout_user(
        db=db,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        user_id=current_user.id,
    )

    return BaseResponse(
        success=True,
        message=f"Logged out successfully. {count} session(s) terminated.",
    )


@router.get("/me", response_model=BaseResponse[UserWithContext])
async def get_current_user_info(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get current user's profile with account and company context."""
    # Fetch full user data from database
    user = await crud.get_user_by_id(
        db,
        user_id=current_user.id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
    )

    if not user:
        from ...core.exceptions import NotFoundError

        raise NotFoundError("User not found")

    # Get account and company names
    account = await crud.get_account_by_id(db, current_user.account_id)
    company = await crud.get_company_by_id(db, current_user.company_id)

    return BaseResponse(
        success=True,
        data=UserWithContext(
            id=user.id,
            uuid=user.uuid,
            account_id=user.account_id,
            company_id=user.company_id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role_id=user.role_id,
            role=RoleResponse.model_validate(user.role) if user.role else None,
            is_active=user.is_active,
            last_login=user.last_login,
            created_at=user.created_at,
            account_name=account.name if account else "Unknown",
            company_name=company.name if company else "Unknown",
        ),
    )


@router.post("/change-password", response_model=BaseResponse[None])
async def change_password(
    current_user: CurrentUser,
    password_data: ChangePasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Change current user's password."""
    await services.change_password(
        db=db,
        user_id=current_user.id,
        account_id=current_user.account_id,
        company_id=current_user.company_id,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
    )

    return BaseResponse(
        success=True,
        message="Password changed successfully. Please login again.",
    )


@router.get("/roles", response_model=BaseResponse[list[RoleResponse]])
async def list_roles(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get all available roles."""
    roles = await crud.get_all_roles(db)

    return BaseResponse(
        success=True,
        data=[RoleResponse.model_validate(role) for role in roles],
    )
