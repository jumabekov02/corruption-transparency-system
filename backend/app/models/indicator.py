from sqlalchemy import Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import IndicatorType


class Indicator(Base):
    """One risk rule's result for one contract (the D4 indicators)."""

    __tablename__ = "indicators"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    type: Mapped[IndicatorType] = mapped_column(Enum(IndicatorType), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
