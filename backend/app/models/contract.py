from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ContractStatus

if TYPE_CHECKING:
    from app.models.indicator import Indicator
    from app.models.risk_score import RiskScore


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)

    # One contract per tender => unique foreign key (a 1-to-1 link).
    tender_id: Mapped[int] = mapped_column(ForeignKey("tenders.id"), unique=True, nullable=False)
    contractor_id: Mapped[int] = mapped_column(ForeignKey("contractors.id"), nullable=False)

    awarded_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    final_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))

    start_date: Mapped[date | None] = mapped_column(Date)
    planned_end: Mapped[date | None] = mapped_column(Date)
    actual_end: Mapped[date | None] = mapped_column(Date)

    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus), default=ContractStatus.in_progress, nullable=False
    )

    # Read-only navigation to the risk results (written by the risk engine).
    risk_score: Mapped["RiskScore | None"] = relationship(viewonly=True, uselist=False)
    indicators: Mapped[list["Indicator"]] = relationship(viewonly=True)
