from pydantic import BaseModel, ConfigDict

from app.models.enums import Role


class Token(BaseModel):
    """What the login endpoint returns."""

    access_token: str
    token_type: str = "bearer"
    role: Role
    user_id: int


class UserRead(BaseModel):
    """A safe view of a user — note: no password field is ever exposed."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: Role
    is_active: bool
