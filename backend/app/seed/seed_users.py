"""Create demo login accounts (+ a demo contractor company). Run with:

    docker compose exec backend python -m app.seed.seed_users

Idempotent: safe to run repeatedly.
"""
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.contractor import Contractor
from app.models.enums import Role
from app.models.user import User

DEMO_CONTRACTOR_VAT = "IT00000000000"


def run() -> None:
    db = SessionLocal()
    try:
        # A company that the contractor login represents, so it can submit bids.
        demo_co = db.scalar(
            select(Contractor).where(Contractor.vat_id == DEMO_CONTRACTOR_VAT)
        )
        if demo_co is None:
            demo_co = Contractor(
                name="Demo Contractor S.p.A.", vat_id=DEMO_CONTRACTOR_VAT, country="IT"
            )
            db.add(demo_co)
            db.flush()  # assign demo_co.id without committing yet

        # (email, password, role, contractor_id)
        demo_users = [
            ("admin@demo.local", "admin", Role.admin, None),
            ("analyst@demo.local", "analyst", Role.analyst, None),
            ("contractor@demo.local", "contractor", Role.contractor, demo_co.id),
        ]
        for email, password, role, contractor_id in demo_users:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                db.add(
                    User(
                        email=email,
                        hashed_password=hash_password(password),
                        role=role,
                        contractor_id=contractor_id,
                    )
                )
            elif role == Role.contractor and user.contractor_id is None:
                # Link an already-existing contractor account to the demo company.
                user.contractor_id = contractor_id

        db.commit()
        print("Seed complete (users + demo contractor).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
