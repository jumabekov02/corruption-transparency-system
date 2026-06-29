from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Contractor(Base):
    __tablename__ = "contractors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # vat_id is the company's tax number — the natural unique identifier.
    vat_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    # ISO country code (e.g. "IT"); defaults to Italy when not provided.
    country: Mapped[str] = mapped_column(String(2), default="IT", nullable=False)

    registration_date: Mapped[date | None] = mapped_column(Date)
