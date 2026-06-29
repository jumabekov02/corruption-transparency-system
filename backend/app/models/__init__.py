# Import every model here so that:
#   1) `Base.metadata` knows about all tables (Alembic autogenerate needs this), and
#   2) you can write `from app.models import Department, ...` elsewhere.
#
# Add one line per new model file as you create it.
from app.db.base import Base
from app.models.bid import Bid
from app.models.contract import Contract
from app.models.contractor import Contractor
from app.models.department import Department
from app.models.indicator import Indicator
from app.models.log import Log
from app.models.risk_score import RiskScore
from app.models.tender import Tender
from app.models.user import User

__all__ = [
    "Base",
    "Department",
    "Contractor",
    "User",
    "Tender",
    "Bid",
    "Contract",
    "Indicator",
    "RiskScore",
    "Log",
]
