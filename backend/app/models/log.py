from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Log(Base):
    """Audit trail: who did what, when (the D6 activity log)."""

    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable: some actions (e.g. the system auto-awarding) have no human user.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[int | None] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    payload: Mapped[dict | None] = mapped_column(JSONB)
