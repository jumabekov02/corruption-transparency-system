from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import BidStatus


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[int] = mapped_column(primary_key=True)
    tender_id: Mapped[int] = mapped_column(ForeignKey("tenders.id"), nullable=False)
    contractor_id: Mapped[int] = mapped_column(ForeignKey("contractors.id"), nullable=False)

    # --- What the bidder offers ---
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    delivery_days: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_score: Mapped[int | None] = mapped_column(Integer)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[BidStatus] = mapped_column(
        Enum(BidStatus), default=BidStatus.submitted, nullable=False
    )
    exclusion_reason: Mapped[str | None] = mapped_column(Text)

    # --- Filled in by the awarding engine (C1/C2) at tender close ---
    norm_price: Mapped[float | None] = mapped_column(Float)
    norm_time: Mapped[float | None] = mapped_column(Float)
    norm_quality: Mapped[float | None] = mapped_column(Float)
    weighted_total: Mapped[float | None] = mapped_column(Float)
    rank: Mapped[int | None] = mapped_column(Integer)
    is_anomalous_low: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    explanation: Mapped[dict | None] = mapped_column(JSONB)
