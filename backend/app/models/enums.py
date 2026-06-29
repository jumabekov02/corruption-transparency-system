import enum


class Role(str, enum.Enum):
    contractor = "contractor"
    analyst = "analyst"
    admin = "admin"


class TenderStatus(str, enum.Enum):
    draft = "draft"
    open = "open"
    closed = "closed"
    awarded = "awarded"
    void = "void"


class BidStatus(str, enum.Enum):
    submitted = "submitted"
    withdrawn = "withdrawn"
    admitted = "admitted"
    excluded = "excluded"


class ContractStatus(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class IndicatorType(str, enum.Enum):
    single_bidder = "single_bidder"
    repeated_winner = "repeated_winner"
    budget_overrun = "budget_overrun"
    delay = "delay"
    price_anomaly = "price_anomaly"


class RiskBand(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
