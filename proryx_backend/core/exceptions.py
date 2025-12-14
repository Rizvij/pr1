"""
Custom exception classes for consistent error handling across all modules.
"""

from typing import Any


class ProRyxException(Exception):
    """Base exception for all ProRyx related errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ResourceNotFoundError(ProRyxException):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        identifier: Any,
        details: dict[str, Any] | None = None,
    ):
        message = f"{resource_type} with identifier '{identifier}' not found"
        super().__init__(message, details)
        self.resource_type = resource_type
        self.identifier = identifier


class ResourceAlreadyExistsError(ProRyxException):
    """Raised when trying to create a resource that already exists."""

    def __init__(
        self,
        resource_type: str,
        identifier: Any,
        details: dict[str, Any] | None = None,
    ):
        message = f"{resource_type} with identifier '{identifier}' already exists"
        super().__init__(message, details)
        self.resource_type = resource_type
        self.identifier = identifier


class ValidationError(ProRyxException):
    """Raised when data validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        details: dict[str, Any] | None = None,
    ):
        if field:
            full_message = f"Validation error for field '{field}': {message}"
        else:
            full_message = message
        super().__init__(full_message, details)
        self.field = field
        self.value = value


class BusinessLogicError(ProRyxException):
    """Raised when business logic constraints are violated."""

    pass


class PermissionError(ProRyxException):
    """Raised when user lacks permission to perform an action."""

    def __init__(
        self, action: str, resource_type: str, details: dict[str, Any] | None = None
    ):
        message = f"Permission denied: cannot {action} {resource_type}"
        super().__init__(message, details)
        self.action = action
        self.resource_type = resource_type


class DatabaseError(ProRyxException):
    """Raised when database operations fail."""

    pass


class AuthenticationError(ProRyxException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, details)


class NotFoundError(ProRyxException):
    """Raised when a resource is not found (simplified version)."""

    def __init__(
        self, message: str = "Resource not found", details: dict[str, Any] | None = None
    ):
        super().__init__(message, details)


class ExternalServiceError(ProRyxException):
    """Raised when external service integration fails."""

    def __init__(
        self,
        service_name: str,
        operation: str,
        details: dict[str, Any] | None = None,
    ):
        message = f"External service '{service_name}' failed during '{operation}'"
        super().__init__(message, details)
        self.service_name = service_name
        self.operation = operation
