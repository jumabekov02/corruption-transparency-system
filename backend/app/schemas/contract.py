from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import ContractStatus, IndicatorType, RiskBand


class RiskSummary(BaseModel):
    """Compact risk view for list responses."""

    model_config = ConfigDict(from_attributes=True)

    total_score: int
    band: RiskBand


class RiskScoreDetail(RiskSummary):
    """Full risk view for the detail response."""

    explanation: str | None = None
    components: dict | None = None


class IndicatorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: IndicatorType
    score: int
    explanation: str | None


class ContractRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tender_id: int
    contractor_id: int
    awarded_value: Decimal
    final_cost: Decimal | None
    start_date: date | None
    planned_end: date | None
    actual_end: date | None
    status: ContractStatus
    risk_score: RiskSummary | None = None  # from the Contract.risk_score relationship


class ContractDetail(ContractRead):
    risk_score: RiskScoreDetail | None = None  # override with the full version
    indicators: list[IndicatorRead] = []
