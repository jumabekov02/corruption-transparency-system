from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import TenderStatus


class TenderBase(BaseModel):
    """Shared, client-editable fields."""

    external_id: str
    department_id: int
    title: str
    description: str | None = None
    estimated_value: Decimal
    closing_at: datetime | None = None
    # MEAT award-criterion weights (default 60/20/20).
    w_price: int = 60
    w_time: int = 20
    w_quality: int = 20


class TenderCreate(TenderBase):
    pass


class TenderUpdate(BaseModel):
    """Every field optional => partial update."""

    title: str | None = None
    description: str | None = None
    estimated_value: Decimal | None = None
    closing_at: datetime | None = None
    w_price: int | None = None
    w_time: int | None = None
    w_quality: int | None = None


class TenderRead(TenderBase):
    model_config = ConfigDict(from_attributes=True)

    # Server-managed fields (set by the system / awarding engine).
    id: int
    status: TenderStatus
    winning_bid_id: int | None
    awarded_at: datetime | None
    award_trace: dict | None = None  # the full explained decision (after closing)
