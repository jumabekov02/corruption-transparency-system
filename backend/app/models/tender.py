from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import TenderStatus


class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    estimated_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[TenderStatus] = mapped_column(
        Enum(TenderStatus), default=TenderStatus.draft, nullable=False
    )

    # MEAT award-criterion weights (percentages meant to sum to 100).
    w_price: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    w_time: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    w_quality: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    # Filled in when the tender is awarded by the engine.
    # use_alter=True breaks the circular link with bids (tenders -> bids -> tenders):
    # Alembic creates both tables first, then adds this foreign key with an ALTER.
    winning_bid_id: Mapped[int | None] = mapped_column(
        ForeignKey("bids.id", use_alter=True, name="fk_tender_winning_bid")
    )
    awarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    award_trace: Mapped[dict | None] = mapped_column(JSONB)
