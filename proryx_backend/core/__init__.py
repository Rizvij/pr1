"""Core infrastructure for ProRyx backend."""

from .base_crud import BaseCRUD
from .database_types import UUID
from .exceptions import (
    BusinessLogicError,
    DatabaseError,
    ExternalServiceError,
    PermissionError,
    ProRyxException,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    ValidationError,
)
from .pagination import PaginatedResults, calculate_offset, validate_pagination_params

__all__ = [
    "BaseCRUD",
    "UUID",
    "ProRyxException",
    "ResourceNotFoundError",
    "ResourceAlreadyExistsError",
    "ValidationError",
    "BusinessLogicError",
    "PermissionError",
    "DatabaseError",
    "ExternalServiceError",
    "PaginatedResults",
    "validate_pagination_params",
    "calculate_offset",
]
