from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import Role


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # We never store the raw password — only its bcrypt hash (added in Sprint 2 auth work).
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Enum(Role) stores one of: contractor | analyst | admin.
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)

    # Foreign key → contractors.id. Nullable: only contractor-role users link to a company.
    contractor_id: Mapped[int | None] = mapped_column(ForeignKey("contractors.id"))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # server_default=func.now() => Postgres fills the timestamp at insert time.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
