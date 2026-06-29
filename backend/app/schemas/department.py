from pydantic import BaseModel, ConfigDict


class DepartmentBase(BaseModel):
    """Fields shared by create/read (the editable data)."""

    name: str
    region: str | None = None


class DepartmentCreate(DepartmentBase):
    """What a client must send to create a department."""

    pass


class DepartmentUpdate(BaseModel):
    """What a client may send to update — every field optional (partial update)."""

    name: str | None = None
    region: str | None = None


class DepartmentRead(DepartmentBase):
    """What the API returns. from_attributes lets Pydantic read straight from a
    SQLAlchemy model instance (model.id, model.name, ...)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
