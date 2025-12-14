"""
Base CRUD operations for consistent data access patterns across all modules.
Adapted for two-level multi-tenancy (account_id + company_id).
"""

from abc import ABC
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from ..modules.commons.schemas import PaginationParams

# Generic type variables for type safety
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseCRUD(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """
    Base CRUD class providing common database operations.

    This class implements standard CRUD operations with two-level multi-tenancy
    (account_id + company_id) for data isolation.

    Attributes:
        model: SQLAlchemy model class
        search_fields: Fields to search in for text-based queries
        default_relationships: Default relationships to load
        default_order_by: Default ordering field
    """

    def __init__(self, model: type[ModelType]):
        """Initialize CRUD operations for a specific model."""
        self.model = model

    # Configuration attributes that can be overridden by subclasses
    search_fields: list[str] = []
    default_relationships: list[str] = []
    default_order_by: str = "created_at"
    default_order_desc: bool = True

    def _apply_tenant_filter(
        self, query: Select, account_id: int, company_id: int
    ) -> Select:
        """Apply tenant filtering for two-level multi-tenancy."""
        return query.where(
            and_(
                self.model.account_id == account_id,
                self.model.company_id == company_id,
            )
        )

    def _apply_active_filter(
        self, query: Select, is_active: bool | None = None
    ) -> Select:
        """Apply is_active filtering if the model supports it."""
        if is_active is not None and hasattr(self.model, "is_active"):
            return query.where(self.model.is_active == is_active)
        return query

    def _apply_search_filter(
        self, query: Select, search_query: str | None = None
    ) -> Select:
        """Apply text-based search filtering across configured search fields."""
        if search_query and self.search_fields:
            search_conditions = []
            for field_name in self.search_fields:
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    search_conditions.append(field.ilike(f"%{search_query}%"))
            if search_conditions:
                query = query.where(or_(*search_conditions))
        return query

    def _apply_custom_filters(
        self, query: Select, filters: dict[str, Any] | None = None
    ) -> Select:
        """Apply additional custom filters."""
        if not filters:
            return query

        for field_name, value in filters.items():
            if value is not None and hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                query = query.where(field == value)
        return query

    def _apply_relationships(
        self, query: Select, load_relationships: list[str] | None = None
    ) -> Select:
        """Apply relationship loading."""
        relationships = load_relationships or self.default_relationships
        for relationship_name in relationships:
            if hasattr(self.model, relationship_name):
                relationship = getattr(self.model, relationship_name)
                query = query.options(selectinload(relationship))
        return query

    def _apply_ordering(self, query: Select, order_by: str | None = None) -> Select:
        """Apply ordering to query."""
        order_field = order_by or self.default_order_by
        if hasattr(self.model, order_field):
            field = getattr(self.model, order_field)
            if self.default_order_desc:
                query = query.order_by(field.desc())
            else:
                query = query.order_by(field)
        return query

    async def create(
        self,
        db: AsyncSession,
        obj_in: CreateSchemaType | dict[str, Any],
        account_id: int,
        company_id: int,
        **kwargs,
    ) -> ModelType:
        """
        Create a new record.

        Args:
            db: Database session
            obj_in: Data for creating the record
            account_id: Account ID for multi-tenancy
            company_id: Company ID for multi-tenancy
            **kwargs: Additional fields to set on the model

        Returns:
            The created model instance
        """
        if isinstance(obj_in, dict):
            obj_data = obj_in
        else:
            obj_data = obj_in.model_dump(exclude_unset=True)

        obj_data["account_id"] = account_id
        obj_data["company_id"] = company_id
        obj_data.update(kwargs)

        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get(
        self,
        db: AsyncSession,
        account_id: int,
        company_id: int,
        id: int,
        load_relationships: list[str] | None = None,
    ) -> ModelType | None:
        """
        Get a single record by composite key (account_id, company_id, id).

        Args:
            db: Database session
            account_id: Account ID
            company_id: Company ID
            id: Record ID
            load_relationships: Relationships to eager load

        Returns:
            The model instance or None if not found
        """
        query = select(self.model).where(
            and_(
                self.model.account_id == account_id,
                self.model.company_id == company_id,
                self.model.id == id,
            )
        )

        query = self._apply_relationships(query, load_relationships)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_uuid(
        self,
        db: AsyncSession,
        account_id: int,
        company_id: int,
        uuid: UUID,
        load_relationships: list[str] | None = None,
    ) -> ModelType | None:
        """
        Get a single record by UUID.

        Args:
            db: Database session
            account_id: Account ID
            company_id: Company ID
            uuid: Record UUID
            load_relationships: Relationships to eager load

        Returns:
            The model instance or None if not found
        """
        query = select(self.model).where(
            and_(
                self.model.account_id == account_id,
                self.model.company_id == company_id,
                self.model.uuid == uuid,
            )
        )

        query = self._apply_relationships(query, load_relationships)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        account_id: int,
        company_id: int,
        pagination: PaginationParams,
        is_active: bool | None = None,
        search_query: str | None = None,
        filters: dict[str, Any] | None = None,
        load_relationships: list[str] | None = None,
        order_by: str | None = None,
    ) -> tuple[list[ModelType], int]:
        """
        Get multiple records with pagination, filtering, and search.

        Args:
            db: Database session
            account_id: Account ID
            company_id: Company ID
            pagination: Pagination parameters
            is_active: Filter by active status
            search_query: Text search query
            filters: Additional filters to apply
            load_relationships: Relationships to eager load
            order_by: Field to order by

        Returns:
            Tuple of (records, total_count)
        """
        query = select(self.model)
        query = self._apply_tenant_filter(query, account_id, company_id)
        query = self._apply_active_filter(query, is_active)
        query = self._apply_search_filter(query, search_query)
        query = self._apply_custom_filters(query, filters)
        query = self._apply_relationships(query, load_relationships)
        query = self._apply_ordering(query, order_by)

        # Get total count
        count_query = select(func.count(self.model.id))
        count_query = self._apply_tenant_filter(count_query, account_id, company_id)
        count_query = self._apply_active_filter(count_query, is_active)
        count_query = self._apply_search_filter(count_query, search_query)
        count_query = self._apply_custom_filters(count_query, filters)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        if pagination.page and pagination.page_size:
            offset = (pagination.page - 1) * pagination.page_size
            query = query.offset(offset).limit(pagination.page_size)

        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(
        self,
        db: AsyncSession,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """
        Update a record.

        Args:
            db: Database session
            db_obj: Existing database object
            obj_in: Update data

        Returns:
            The updated model instance
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(
        self, db: AsyncSession, db_obj: ModelType, soft_delete: bool = True
    ) -> ModelType:
        """
        Delete a record (soft delete by default).

        Args:
            db: Database session
            db_obj: Database object to delete
            soft_delete: Whether to soft delete (set is_active=False) or hard delete

        Returns:
            The deleted/deactivated model instance
        """
        if soft_delete and hasattr(db_obj, "is_active"):
            db_obj.is_active = False
            await db.commit()
            await db.refresh(db_obj)
        else:
            db.delete(db_obj)
            await db.commit()

        return db_obj

    async def exists(
        self, db: AsyncSession, account_id: int, company_id: int, **filters
    ) -> bool:
        """
        Check if a record exists with the given filters.

        Args:
            db: Database session
            account_id: Account ID
            company_id: Company ID
            **filters: Field filters to check

        Returns:
            True if record exists, False otherwise
        """
        query = select(func.count(self.model.id)).where(
            and_(
                self.model.account_id == account_id,
                self.model.company_id == company_id,
            )
        )

        for field_name, value in filters.items():
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                query = query.where(field == value)

        result = await db.execute(query)
        count = result.scalar() or 0
        return count > 0

    async def count(
        self,
        db: AsyncSession,
        account_id: int,
        company_id: int,
        is_active: bool | None = None,
        **filters,
    ) -> int:
        """
        Count records matching the given criteria.

        Args:
            db: Database session
            account_id: Account ID
            company_id: Company ID
            is_active: Filter by active status
            **filters: Additional field filters

        Returns:
            Count of matching records
        """
        query = select(func.count(self.model.id)).where(
            and_(
                self.model.account_id == account_id,
                self.model.company_id == company_id,
            )
        )

        if is_active is not None and hasattr(self.model, "is_active"):
            query = query.where(self.model.is_active == is_active)

        for field_name, value in filters.items():
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                query = query.where(field == value)

        result = await db.execute(query)
        return result.scalar() or 0
