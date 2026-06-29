from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate

# A router groups related endpoints. prefix => every path here starts with /departments.
# tags => groups them under "departments" in the /docs page.
router = APIRouter(prefix="/departments", tags=["departments"])


# Depends(get_db) is "dependency injection": FastAPI calls get_db(), hands us a fresh
# database session for this request, and closes it automatically afterwards.


@router.get("", response_model=list[DepartmentRead])
def list_departments(db: Session = Depends(get_db)):
    # select(...) builds the query; db.scalars(...).all() runs it and returns model objects.
    return db.scalars(select(Department).order_by(Department.id)).all()


@router.post("", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db)):
    # payload is already validated by Pydantic. model_dump() -> a plain dict of its fields.
    department = Department(**payload.model_dump())
    db.add(department)       # stage the new row
    db.commit()              # write it to Postgres
    db.refresh(department)   # reload it so we get the DB-generated id
    return department


@router.get("/{department_id}", response_model=DepartmentRead)
def get_department(department_id: int, db: Session = Depends(get_db)):
    department = db.get(Department, department_id)  # fetch by primary key
    if department is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return department


@router.patch("/{department_id}", response_model=DepartmentRead)
def update_department(department_id: int, payload: DepartmentUpdate, db: Session = Depends(get_db)):
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    # exclude_unset=True => only the fields the client actually sent get changed.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(department, field, value)
    db.commit()
    db.refresh(department)
    return department


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(department_id: int, db: Session = Depends(get_db)):
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    db.delete(department)
    db.commit()
    # 204 No Content => successful, nothing to return.
