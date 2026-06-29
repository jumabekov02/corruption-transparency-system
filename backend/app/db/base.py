from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Parent class for every model. SQLAlchemy collects all tables that inherit
    from this Base into Base.metadata, which Alembic reads to generate migrations."""

    pass
