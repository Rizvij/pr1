"""Authentication dependencies for FastAPI."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .jwt_service import decode_access_token
from .models import RoleSlug
from .schemas import AuthenticatedUser

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> AuthenticatedUser:
    """Extract and validate current user from JWT token.

    This dependency decodes the JWT token and returns the authenticated user.
    It does NOT make a database call - all user info is in the token.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return AuthenticatedUser(
            id=int(payload["sub"]),
            uuid=payload.get("uuid"),  # Optional - may not be in token
            account_id=payload["account_id"],
            company_id=payload["company_id"],
            email=payload["email"],
            first_name=payload.get("first_name", ""),
            last_name=payload.get("last_name"),
            role_slug=payload["role"],
            is_active=True,  # If token is valid, user was active at token creation
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token payload: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(*allowed_roles: str | RoleSlug):
    """Dependency factory for role-based access control.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            current_user: AuthenticatedUser = Depends(require_role(RoleSlug.ADMIN))
        ):
            ...

        @router.get("/managers-or-admin")
        async def managers_endpoint(
            current_user: AuthenticatedUser = Depends(
                require_role(RoleSlug.ADMIN, RoleSlug.MANAGER)
            )
        ):
            ...
    """
    # Convert all roles to string slugs for comparison
    role_slugs = {r.value if isinstance(r, RoleSlug) else r for r in allowed_roles}

    async def role_checker(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if current_user.role_slug not in role_slugs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(role_slugs)}",
            )
        return current_user

    return role_checker


# Type alias for dependency injection
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
AdminUser = Annotated[AuthenticatedUser, Depends(require_role(RoleSlug.ADMIN))]
ManagerUser = Annotated[
    AuthenticatedUser, Depends(require_role(RoleSlug.ADMIN, RoleSlug.MANAGER))
]
