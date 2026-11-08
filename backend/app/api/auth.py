from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.responses import ok
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import Donor, Hospital, User
from app.schemas import DonorOut, HospitalOut, LoginIn, MeOut, RegisterIn, UserOut
from app.services.audit import log_event
from app.services.geo import lookup_city

router = APIRouter(prefix="/auth", tags=["Auth"])


def _me(db: Session, user: User) -> dict:
    hospital = db.query(Hospital).filter(Hospital.user_id == user.id).first()
    donor = db.query(Donor).filter(Donor.user_id == user.id).first()
    return MeOut(
        user=UserOut.model_validate(user),
        hospital=HospitalOut.model_validate(hospital) if hospital else None,
        donor=DonorOut.model_validate(donor) if donor else None,
    ).model_dump()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    if body.role == "donor" and not body.blood_group:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "blood_group is required for donors")
    if body.role == "hospital" and not body.hospital_name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "hospital_name is required for hospitals")

    lat, lon = body.latitude, body.longitude
    if lat is None or lon is None:
        found = lookup_city(body.city)
        lat, lon = found[1] if found else (None, None)

    user = User(name=body.name, email=email, password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    db.flush()
    if body.role == "hospital":
        db.add(Hospital(user_id=user.id, name=body.hospital_name, city=body.city, latitude=lat, longitude=lon))
    else:
        db.add(Donor(
            user_id=user.id, blood_group=body.blood_group, city=body.city, latitude=lat, longitude=lon,
            availability="available",
            demo_eligibility={"status": "eligible_demo", "response_rate": 0.5, "donation_history": [],
                              "note": "Synthetic demo field - not a medical eligibility decision"},
        ))
    log_event(db, action="user.registered", entity_type="user", entity_id=user.id,
              actor_type="user", actor_id=user.id, meta={"role": body.role})
    db.commit()
    token = create_access_token(str(user.id), user.role)
    return ok({"access_token": token, "token_type": "bearer", "me": _me(db, user)}, "Registered successfully")


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    token = create_access_token(str(user.id), user.role)
    return ok({"access_token": token, "token_type": "bearer", "me": _me(db, user)}, "Logged in")


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(_me(db, user))
