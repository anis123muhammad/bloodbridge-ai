"""SQLAlchemy models. All records in this project are synthetic demo data."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.utils.time import utcnow

# JSONB on Postgres, plain JSON elsewhere (lets tests run on SQLite)
JSONType = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)  # hospital | donor | admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    hospital: Mapped["Hospital | None"] = relationship(back_populates="user", uselist=False)
    donor: Mapped["Donor | None"] = relationship(back_populates="user", uselist=False)


class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(120), index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="hospital")
    requests: Mapped[list["BloodRequest"]] = relationship(back_populates="hospital")


class Donor(Base):
    __tablename__ = "donors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    blood_group: Mapped[str] = mapped_column(String(3), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    # available | temporarily_unavailable | unavailable
    availability: Mapped[str] = mapped_column(String(30), default="available", index=True)
    # Synthetic demo fields, e.g. {"status": "eligible_demo", "last_donation_date": "...",
    # "donation_history": [...]} -- never real medical data.
    demo_eligibility: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="donor")


class BloodRequest(Base):
    __tablename__ = "blood_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(200))
    blood_group: Mapped[str] = mapped_column(String(3), index=True)
    units_requested: Mapped[int] = mapped_column(Integer)
    urgency: Mapped[str] = mapped_column(String(20))  # normal | urgent | critical
    priority: Mapped[str | None] = mapped_column(String(20), index=True)  # low | medium | high | critical
    priority_score: Mapped[int | None] = mapped_column(Integer)
    priority_reason: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(200))
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text)
    contact_info: Mapped[str | None] = mapped_column(String(200))  # demo contact only
    # draft | submitted | processing | awaiting_approval | inviting_donors |
    # partially_fulfilled | fulfilled | closed | cancelled
    status: Mapped[str] = mapped_column(String(30), default="submitted", index=True)
    status_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    hospital: Mapped[Hospital] = relationship(back_populates="requests")
    matches: Mapped[list["DonorMatch"]] = relationship(back_populates="request")
    invitations: Mapped[list["Invitation"]] = relationship(back_populates="request")


class DonorMatch(Base):
    __tablename__ = "donor_matches"
    __table_args__ = (UniqueConstraint("request_id", "donor_id", name="uq_match_request_donor"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("blood_requests.id", ondelete="CASCADE"), index=True)
    donor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("donors.id", ondelete="CASCADE"), index=True)
    match_score: Mapped[int] = mapped_column(Integer)
    distance_km: Mapped[float | None] = mapped_column(Float)
    match_reasons: Mapped[list[str]] = mapped_column(JSONType, default=list)
    status: Mapped[str] = mapped_column(String(20), default="suggested")  # suggested | approved | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    request: Mapped[BloodRequest] = relationship(back_populates="matches")
    donor: Mapped[Donor] = relationship()


class Invitation(Base):
    __tablename__ = "invitations"
    # One invitation per donor per request -> retries can never create duplicates.
    __table_args__ = (UniqueConstraint("request_id", "donor_id", name="uq_invitation_request_donor"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("blood_requests.id", ondelete="CASCADE"), index=True)
    donor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("donors.id", ondelete="CASCADE"), index=True)
    match_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("donor_matches.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|accepted|declined|expired
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_message: Mapped[str | None] = mapped_column(Text)
    response_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONType)

    request: Mapped[BloodRequest] = relationship(back_populates="invitations")
    donor: Mapped[Donor] = relationship()


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("blood_requests.id", ondelete="CASCADE"), index=True
    )
    agent_name: Mapped[str] = mapped_column(String(60), index=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # pending|running|completed|failed
    input_summary: Mapped[str | None] = mapped_column(Text)
    output_summary: Mapped[str | None] = mapped_column(Text)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    actor_type: Mapped[str] = mapped_column(String(20))  # user | agent | system
    actor_id: Mapped[str | None] = mapped_column(String(80))  # user id or agent name
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("blood_requests.id", ondelete="CASCADE"), index=True
    )
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
