from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import RiskBand


class RiskScore(Base):
    """The fused 0-100 risk verdict for one contract (the C3 output)."""

    __tablename__ = "risk_scores"

    # contract_id is BOTH the primary key AND a foreign key:
    # exactly one risk score per contract, identified by that contract.
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), primary_key=True)

    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    band: Mapped[RiskBand] = mapped_column(Enum(RiskBand), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # The per-source breakdown that produced total_score (rules + ML + awarding flags).
    components: Mapped[dict | None] = mapped_column(JSONB)
    explanation: Mapped[str | None] = mapped_column(Text)
