from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Return a timezone-aware UTC datetime (required by SQLModel's UTCDateTime)."""
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """An account that owns products, competitors and their data."""

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime = Field(default_factory=utcnow)


class Product(SQLModel, table=True):
    """A product you sell and monitor against competitors."""

    __table_args__ = (UniqueConstraint("user_id", "sku", name="uq_product_user_sku"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    sku: str = Field(index=True)
    name: str
    brand: str
    category: str
    ean: str | None = None
    image_url: str | None = None
    cost_price: float = 0.0
    current_price: float
    msrp: float | None = None
    map_price: float | None = None
    currency: str = "EUR"
    strategy: str = "margin_protected"
    min_margin_pct: float = 15.0
    active: bool = True
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Competitor(SQLModel, table=True):
    """A competitor retailer/marketplace whose prices we track."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str
    domain: str
    type: str = "retailer"  # marketplace | retailer
    currency: str = "EUR"
    active: bool = True
    price_source_type: str = "simulated"  # simulated | url
    price_source_config: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class PricePoint(SQLModel, table=True):
    """A single observed competitor price at a point in time."""

    __table_args__ = (
        Index("ix_pricepoint_product_competitor_time", "product_id", "competitor_id", "captured_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    competitor_id: int = Field(foreign_key="competitor.id", index=True)
    price: float | None = None
    currency: str = "EUR"
    stock_status: str = "in_stock"  # in_stock | out_of_stock | unknown
    url: str | None = None
    captured_at: datetime = Field(default_factory=utcnow, index=True)


class Alert(SQLModel, table=True):
    """A pricing event worth surfacing to the user."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    competitor_id: int | None = Field(default=None, foreign_key="competitor.id", index=True)
    type: str
    severity: str = "info"  # critical | warning | info
    message: str
    read: bool = False
    created_at: datetime = Field(default_factory=utcnow, index=True)
