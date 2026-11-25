import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.common import Pagination, donor_out
from app.core.deps import get_current_donor, get_current_user, require_roles
from app.core.responses import ok, paginated
from app.db.session import get_db
from app.models import Donor, User
from app.schemas import AvailabilityIn, DonorUpdateIn
from app.services.audit import log_event
from app.services.geo import lookup_city

router = APIRouter(prefix="/donors", tags=["Donors"])


@router.get("")
def list_donors(
    page: Pagination = Depends(),
    blood_group: str | None = None,
    availability: str | None = None,
    city: str | None = None,
    search: str | None = None,
    _: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    q = select(Donor).join(User, Donor.user_id == User.id)
    if blood_group:
        q = q.where(Donor.blood_group == blood_group.upper().replace(" ", "+"))
    if availability:
        q = q.where(Donor.availability == availability)
    if city:
        q = q.where(Donor.city.ilike(f"%{city}%"))
    if search:
        q = q.where(User.name.ilike(f"%{search}%"))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.order_by(User.name).offset(page.offset).limit(page.page_size)).all()
    return paginated([donor_out(d) for d in items], total, page.page, page.page_size)


@router.get("/me")
def my_profile(donor: Donor = Depends(get_current_donor)):
    return ok(donor_out(donor))


@router.patch("/me")
def update_my_profile(body: DonorUpdateIn, donor: Donor = Depends(get_current_donor),
                      db: Session = Depends(get_db)):
    changes = body.model_dump(exclude_unset=True)
    if "name" in changes:
        donor.user.name = changes.pop("name")
    if "city" in changes and ("latitude" not in changes or "longitude" not in changes):
        found = lookup_city(changes["city"])
        if found:
            changes["latitude"], changes["longitude"] = found[1]
    for k, v in changes.items():
        setattr(donor, k, v)
    log_event(db, action="donor.profile_updated", entity_type="donor", entity_id=donor.id,
              actor_type="user", actor_id=donor.user_id, meta={"fields": list(body.model_dump(exclude_unset=True))})
    db.commit()
    db.refresh(donor)
    return ok(donor_out(donor), "Profile updated")


@router.patch("/{donor_id}/availability")
def set_availability(donor_id: uuid.UUID, body: AvailabilityIn, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    donor = db.get(Donor, donor_id)
    if donor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Donor not found")
    if not (user.role == "admin" or donor.user_id == user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only change your own availability")
    old = donor.availability
    donor.availability = body.availability
    log_event(db, action="donor.availability_updated", entity_type="donor", entity_id=donor.id,
              actor_type="user", actor_id=user.id, meta={"from": old, "to": body.availability})
    db.commit()
    db.refresh(donor)
    return ok(donor_out(donor), "Availability updated")
