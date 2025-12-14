"""
Shared pagination utilities for consistent pagination across all modules.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResults(BaseModel, Generic[T]):
    """
    Generic paginated results container.

    This provides a consistent response structure for all paginated endpoints
    across the application.
    """

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

    @classmethod
    def create(
        cls, items: list[T], total: int, page: int, page_size: int
    ) -> "PaginatedResults[T]":
        """
        Create paginated results with calculated metadata.

        Args:
            items: List of items for current page
            total: Total number of items across all pages
            page: Current page number (1-based)
            page_size: Number of items per page

        Returns:
            PaginatedResults instance with calculated metadata
        """
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        has_next = page < total_pages
        has_previous = page > 1

        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
        )


def validate_pagination_params(page: int, page_size: int) -> tuple[int, int]:
    """
    Validate and normalize pagination parameters.

    Args:
        page: Page number (1-based)
        page_size: Number of items per page

    Returns:
        Tuple of (validated_page, validated_page_size)

    Raises:
        ValueError: If parameters are invalid
    """
    if page < 1:
        raise ValueError("Page must be >= 1")

    if page_size < 1:
        raise ValueError("Page size must be >= 1")

    max_page_size = 100
    if page_size > max_page_size:
        raise ValueError(f"Page size cannot exceed {max_page_size}")

    return page, page_size


def calculate_offset(page: int, page_size: int) -> int:
    """
    Calculate database offset for pagination.

    Args:
        page: Page number (1-based)
        page_size: Number of items per page

    Returns:
        Database offset (0-based)
    """
    return (page - 1) * page_size
