"""Authentication module for ProRyx."""

from .dependencies import (
    AdminUser,
    CurrentUser,
    ManagerUser,
    get_current_user,
    require_role,
)
from .models import Account, Company, RefreshToken, Role, RoleSlug, User
from .routers import router
from .schemas import AuthenticatedUser

__all__ = [
    # Models
    "Account",
    "Company",
    "User",
    "Role",
    "RoleSlug",
    "RefreshToken",
    # Router
    "router",
    # Dependencies
    "get_current_user",
    "require_role",
    "CurrentUser",
    "AdminUser",
    "ManagerUser",
    # Schemas
    "AuthenticatedUser",
]
