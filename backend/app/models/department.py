from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Department(Base):
    # The real table name in Postgres.
    __tablename__ = "departments"

    # Mapped[int] tells both Python and SQLAlchemy the column type.
    # primary_key=True makes this the unique row id (auto-incremented by Postgres).
    id: Mapped[int] = mapped_column(primary_key=True)

    # A required text column, max length 200. Mapped[str] (no None) => NOT NULL.
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Mapped[str | None] => the column is nullable (region is optional).
    region: Mapped[str | None] = mapped_column(String(100))
