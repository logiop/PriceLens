from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Strategy = Literal["match_min", "undercut", "margin_protected", "premium"]

EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


# ------------------------------------------------------------------- Auth
class UserRegister(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=EMAIL_RE)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


# ------------------------------------------------------------------ Teams
class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class TeamRead(BaseModel):
    id: int
    name: str
    role: str
    member_count: int = 0
    created_at: datetime


class TeamMemberCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=EMAIL_RE)
    role: Literal["admin", "member"] = "member"


class TeamMemberRead(BaseModel):
    user_id: int
    email: str
    role: str
    created_at: datetime


# ------------------------------------------------------------------ Audit
class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    action: str
    entity: str | None
    entity_id: int | None
    detail: str | None
    ip: str | None
    created_at: datetime
    user_email: str | None = None


# ---------------------------------------------------------------- Products
class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1)
    brand: str = Field(default="")
    category: str = Field(default="")
    ean: str | None = None
    image_url: str | None = None
    cost_price: float = Field(default=0.0, ge=0)
    current_price: float = Field(gt=0)
    msrp: float | None = Field(default=None, gt=0)
    map_price: float | None = Field(default=None, gt=0)
    currency: str = "EUR"
    strategy: Strategy = "margin_protected"
    min_margin_pct: float = Field(default=15.0, ge=0, le=100)
    active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1)
    brand: str | None = None
    category: str | None = None
    ean: str | None = None
    image_url: str | None = None
    cost_price: float | None = Field(default=None, ge=0)
    current_price: float | None = Field(default=None, gt=0)
    msrp: float | None = Field(default=None, gt=0)
    map_price: float | None = Field(default=None, gt=0)
    currency: str | None = None
    strategy: Strategy | None = None
    min_margin_pct: float | None = Field(default=None, ge=0, le=100)
    active: bool | None = None


class CompetitorPrice(BaseModel):
    competitor_id: int
    competitor_name: str
    domain: str
    price: float | None
    currency: str
    stock_status: str
    url: str | None
    captured_at: datetime | None
    change_pct: float | None = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    # computed market stats (populated by the API)
    competitors_tracked: int = 0
    min_price: float | None = None
    max_price: float | None = None
    avg_price: float | None = None
    position: int | None = None  # 1 = cheapest among competitors
    price_index: float | None = None  # 0-100, higher = more competitive
    open_alerts: int = 0
    last_change_pct: float | None = None
    recommendation: "RepricingRecommendation | None" = None


class ProductDetail(ProductRead):
    competitors: list[CompetitorPrice] = []


# ------------------------------------------------------------- Competitors
class CompetitorBase(BaseModel):
    name: str = Field(min_length=1)
    domain: str = Field(default="")
    type: Literal["retailer", "marketplace"] = "retailer"
    currency: str = "EUR"
    active: bool = True
    price_source_type: Literal["simulated", "url"] = "simulated"
    price_source_config: dict = Field(default_factory=dict)


class CompetitorCreate(CompetitorBase):
    pass


class CompetitorUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    type: Literal["retailer", "marketplace"] | None = None
    currency: str | None = None
    active: bool | None = None
    price_source_type: Literal["simulated", "url"] | None = None
    price_source_config: dict | None = None


class CompetitorRead(CompetitorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    products_tracked: int = 0


# ------------------------------------------------------------------ Alerts
class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    competitor_id: int | None
    type: str
    severity: str
    message: str
    read: bool
    created_at: datetime
    product_name: str | None = None
    competitor_name: str | None = None


# -------------------------------------------------------------- Repricing
class RepricingRecommendation(BaseModel):
    product_id: int
    sku: str
    name: str
    current_price: float
    suggested_price: float
    margin_pct: float
    delta_pct: float
    rationale: str
    new_position: int | None = None
    floor: float | None = None
    ceiling: float | None = None


class RepricingPreview(BaseModel):
    recommendations: list[RepricingRecommendation]
    total_potential_margin_impact: float | None = None


class ApplyRecommendation(BaseModel):
    product_id: int
    suggested_price: float


# ---------------------------------------------------------------- Collect
class CollectResult(BaseModel):
    collected: int
    alerts_created: int
    skipped: int
    errors: int


class HistoryPoint(BaseModel):
    captured_at: datetime
    price: float | None


class HistorySeries(BaseModel):
    competitor_id: int
    competitor_name: str
    domain: str
    points: list[HistoryPoint]
