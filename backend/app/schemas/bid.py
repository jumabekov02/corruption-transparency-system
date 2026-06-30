from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import BidStatus


class BidCreate(BaseModel):
    """What a contractor submits. tender_id comes from the URL, contractor_id
    from the logged-in user — so neither is in the request body."""

    price: Decimal
    delivery_days: int
    quality_score: int | None = None


class BidRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tender_id: int
    contractor_id: int
    price: Decimal
    delivery_days: int
    quality_score: int | None
    status: BidStatus
    submitted_at: datetime
    # --- Filled by the awarding engine; null until the tender is closed ---
    weighted_total: float | None
    rank: int | None
    is_anomalous_low: bool
    exclusion_reason: str | None
