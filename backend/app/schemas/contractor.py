from datetime import date

from pydantic import BaseModel, ConfigDict


class ContractorBase(BaseModel):
    name: str
    vat_id: str
    country: str = "IT"
    registration_date: date | None = None


class ContractorCreate(ContractorBase):
    pass


class ContractorUpdate(BaseModel):
    name: str | None = None
    vat_id: str | None = None
    country: str | None = None
    registration_date: date | None = None


class ContractorRead(ContractorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
