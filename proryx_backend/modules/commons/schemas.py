"""Common schemas shared across all modules."""

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SortDirection(str, Enum):
    """Sort direction enum."""

    ASC = "asc"
    DESC = "desc"


class BaseResponse(BaseModel, Generic[T]):
    """Base response schema for API responses."""

    success: bool = Field(
        default=True, description="Whether the request was successful"
    )
    message: str | None = Field(default=None, description="Response message")
    data: T | None = Field(default=None, description="Response data")
    error: Any | None = Field(default=None, description="Error details if any")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_field: str | None = Field(default=None, description="Field to sort by")
    sort_direction: SortDirection | None = Field(
        default=None, description="Sort direction"
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response schema."""

    items: list[T] = Field(default_factory=list, description="List of items")
    total: int = Field(default=0, description="Total number of items")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=20, description="Items per page")
    total_pages: int = Field(default=0, description="Total number of pages")

    @classmethod
    def from_items(cls, items: list[T], total: int, page: int, page_size: int):
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
