"""Authentication schemas for ProRyx."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# ----- Account Schemas -----


class AccountBase(BaseModel):
    """Base account schema."""

    name: str = Field(..., min_length=1, max_length=255)


class AccountCreate(AccountBase):
    """Schema for creating an account."""

    pass


class AccountResponse(AccountBase):
    """Schema for account response."""

    id: int
    uuid: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ----- Company Schemas -----


class CompanyBase(BaseModel):
    """Base company schema."""

    name: str = Field(..., min_length=1, max_length=255)


class CompanyCreate(CompanyBase):
    """Schema for creating a company."""

    account_id: int


class CompanyResponse(CompanyBase):
    """Schema for company response."""

    id: int
    uuid: UUID
    account_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ----- Role Schemas -----


class RoleResponse(BaseModel):
    """Schema for role response."""

    id: int
    slug: str
    name: str
    description: str | None = None

    class Config:
        from_attributes = True


# ----- User Schemas -----


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=120)
    last_name: str | None = Field(None, max_length=120)


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(..., min_length=8, max_length=128)
    role_id: int


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    first_name: str | None = Field(None, min_length=1, max_length=120)
    last_name: str | None = Field(None, max_length=120)
    role_id: int | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    """Schema for user response."""

    id: int
    uuid: UUID
    account_id: int
    company_id: int
    role_id: int
    role: RoleResponse | None = None
    is_active: bool
    last_login: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserWithContext(UserResponse):
    """User response with account and company context."""

    account_name: str
    company_name: str


# ----- Auth Schemas -----


class LoginRequest(BaseModel):
    """Schema for login request."""

    email: EmailStr
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Schema for password change request."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class AuthenticatedUser(BaseModel):
    """Authenticated user context for request handling."""

    id: int
    uuid: UUID | None = None  # Optional - not included in JWT token
    account_id: int
    company_id: int
    email: str
    first_name: str = ""
    last_name: str | None = None
    role_slug: str
    is_active: bool = True

    @property
    def full_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    class Config:
        from_attributes = True
