"""Shared helpers for routers: access checks and response serializers."""
import uuid

from fastapi import HTTPException, Query, status
from sqlalchemy.orm import Session

from app.agents.follow_up import response_counts
from app.models import BloodRequest, Donor, DonorMatch, Hospital, Invitation, User
from app.schemas import DonorWithNameOut, InvitationOut, MatchOut, RequestDetailOut, RequestOut


class Pagination:
    def __init__(self, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def hospital_of(db: Session, user: User) -> Hospital | None:
    return db.query(Hospital).filter(Hospital.user_id == user.id).first()


def donor_of(db: Session, user: User) -> Donor | None:
    return db.query(Donor).filter(Donor.user_id == user.id).first()


def get_request_for_user(db: Session, request_id: uuid.UUID, user: User) -> BloodRequest:
    """Admins see everything; a hospital only sees its own requests (404 otherwise, no leaking)."""
    req = db.get(BloodRequest, request_id)
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    if user.role == "admin":
        return req
    if user.role == "hospital":
        hospital = hospital_of(db, user)
        if hospital and req.hospital_id == hospital.id:
            return req
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")


def request_out(req: BloodRequest) -> dict:
    return RequestOut.model_validate(req).model_dump()


def request_detail_out(req: BloodRequest) -> dict:
    data = RequestOut.model_validate(req).model_dump()
    return RequestDetailOut(**data, hospital_name=req.hospital.name, progress=response_counts(req)).model_dump()


def match_out(m: DonorMatch, invitation_status: str | None = None) -> dict:
    d = m.donor
    return MatchOut(
        id=m.id, request_id=m.request_id, donor_id=m.donor_id, donor_name=d.user.name,
        donor_blood_group=d.blood_group, donor_city=d.city, availability=d.availability,
        distance_km=m.distance_km, match_score=m.match_score, match_reasons=m.match_reasons or [],
        status=m.status, invitation_status=invitation_status,
    ).model_dump()


def invitation_out(inv: Invitation) -> dict:
    r = inv.request
    return InvitationOut(
        id=inv.id, request_id=inv.request_id, donor_id=inv.donor_id, status=inv.status,
        sent_at=inv.sent_at, responded_at=inv.responded_at, response_message=inv.response_message,
        response_analysis=inv.response_analysis, request_blood_group=r.blood_group,
        request_urgency=r.urgency, request_location=r.location, request_deadline=r.deadline,
        hospital_name=r.hospital.name, donor_name=inv.donor.user.name,
    ).model_dump()


def donor_out(d: Donor) -> dict:
    data = DonorWithNameOut.model_validate({**{c: getattr(d, c) for c in (
        "id", "user_id", "blood_group", "city", "latitude", "longitude", "availability",
        "demo_eligibility", "updated_at")}, "name": d.user.name})
    return data.model_dump()
