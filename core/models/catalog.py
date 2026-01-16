from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "categories"

    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    sort_rank: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    parent: Mapped["Category | None"] = relationship(
        "Category", remote_side="Category.id", back_populates="children"
    )
    children: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent"
    )
    items: Mapped[list["Item"]] = relationship(
        "Item",
        secondary="item_categories",
        back_populates="categories",
    )

    __table_args__ = (
        Index("ix_categories_parent_id", "parent_id"),
        Index("ix_categories_is_active", "is_active"),
    )


class Tag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tags"

    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    items: Mapped[list["Item"]] = relationship(
        "Item",
        secondary="item_tags",
        back_populates="tags",
    )


class Item(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "items"

    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    sort_rank: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    min_price_rub: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_price_rub: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    has_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    categories: Mapped[list[Category]] = relationship(
        "Category",
        secondary="item_categories",
        back_populates="items",
    )
    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary="item_tags",
        back_populates="items",
    )
    images: Mapped[list["ItemImage"]] = relationship(
        "ItemImage", back_populates="item", cascade="all, delete-orphan"
    )
    variants: Mapped[list["ItemVariant"]] = relationship(
        "ItemVariant", back_populates="item", cascade="all, delete-orphan"
    )


class ItemCategory(Base):
    __tablename__ = "item_categories"

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id"), primary_key=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), primary_key=True
    )


class ItemTag(Base):
    __tablename__ = "item_tags"

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True
    )

class ItemImage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "item_images"

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id")
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    alt: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_main: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    item: Mapped[Item] = relationship("Item", back_populates="images")


class ItemVariant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "item_variants"

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id")
    )
    sku: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    price_rub: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    compare_at_price_rub: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    stock: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    item: Mapped[Item] = relationship("Item", back_populates="variants")

    __table_args__ = (
        Index("ix_item_variants_item_id", "item_id"),
        Index("ix_item_variants_is_active", "is_active"),
        Index("ix_item_variants_attributes", "attributes", postgresql_using="gin"),
    )


__all__ = [
    "Category",
    "Tag",
    "Item",
    "ItemCategory",
    "ItemTag",
    "ItemImage",
    "ItemVariant",
]
