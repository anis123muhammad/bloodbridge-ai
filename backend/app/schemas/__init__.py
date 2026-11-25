"""Pydantic schemas: request bodies (In) and response shapes (Out)."""
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.services.blood_rules import BLOOD_GROUPS, normalize_blood_group

Role = Literal["hospital", "donor", "admin"]
Urgency = Literal["normal", "urgent", "critical"]
Availability = Literal["available", "temporarily_unavailable", "unavailable"]
RequestStatus = Literal[
    "draft", "submitted", "processing", "awaiting_approval", "inviting_donors",
    "partially_fulfilled", "fulfilled", "closed", "cancelled",
]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _blood_group(v: str | None) -> str | None:
    if v is None:
        return None
    g = normalize_blood_group(v)
    if g not in BLOOD_GROUPS:
        raise ValueError(f"blood_group must be one of {BLOOD_GROUPS}")
    return g


# ---------- Auth ----------
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: Literal["hospital", "donor"]  # admins are created by the seed script only
    city: str = Field(min_length=2, max_length=120)
    latitude: float | None = None
    longitude: float | None = None
    # hospital only
    hospital_name: str | None = None
    # donor only
    blood_group: str | None = None

    @field_validator("blood_group")
    @classmethod
    def validate_blood_group(cls, v: str | None) -> str | None:
        return _blood_group(v)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class HospitalOut(ORM):
    id: uuid.UUID
    name: str
    city: str
    latitude: float | None
    longitude: float | None


class DonorOut(ORM):
    id: uuid.UUID
    user_id: uuid.UUID
    blood_group: str
    city: str
    latitude: float | None
    longitude: float | None
    availability: str
    demo_eligibility: dict[str, Any]
    updated_at: datetime


class DonorWithNameOut(DonorOut):
    name: str


class UserOut(ORM):
    id: uuid.UUID
    name: str
    email: str
    role: str
    created_at: datetime


class MeOut(BaseModel):
    user: UserOut
    hospital: HospitalOut | None = None
    donor: DonorOut | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Requests ----------
class RequestCreateIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    blood_group: str
    units_requested: int = Field(ge=1, le=20)
    urgency: Urgency = "normal"
    location: str | None = Field(default=None, max_length=200)  # defaults to hospital city
    deadline: datetime
    description: str | None = Field(default=None, max_length=2000)
    contact_info: str | None = Field(default=None, max_length=200)
    auto_run_workflow: bool = False

    @field_validator("blood_group")
    @classmethod
    def validate_blood_group(cls, v: str | None) -> str | None:
        return _blood_group(v)


class RequestUpdateIn(BaseModel):
    title: str | None = None
    blood_group: str | None = None
    units_requested: int | None = Field(default=None, ge=1, le=20)
    urgency: Urgency | None = None
    location: str | None = None
    deadline: datetime | None = None
    description: str | None = None
    contact_info: str | None = None
    status: Literal["fulfilled", "closed", "cancelled"] | None = None  # manual transitions only

    @field_validator("blood_group")
    @classmethod
    def validate_blood_group(cls, v: str | None) -> str | None:
        return _blood_group(v)


class AnalyzeTextIn(BaseModel):
    text: str = Field(min_length=5, max_length=2000)


class RequestOut(ORM):
    id: uuid.UUID
    hospital_id: uuid.UUID
    title: str | None
    blood_group: str
    units_requested: int
    urgency: str
    priority: str | None
    priority_score: int | None
    priority_reason: str | None
    location: str
    deadline: datetime
    description: str | None
    contact_info: str | None
    status: str
    status_note: str | None
    created_at: datetime
    updated_at: datetime


class RequestDetailOut(RequestOut):
    hospital_name: str
    progress: dict[str, int]


class MatchOut(ORM):
    id: uuid.UUID
    request_id: uuid.UUID
    donor_id: uuid.UUID
    donor_name: str
    donor_blood_group: str
    donor_city: str
    availability: str
    distance_km: float | None
    match_score: int
    match_reasons: list[str]
    status: str
    invitation_status: str | None = None


class ApproveMatchesIn(BaseModel):
    approve_ids: list[uuid.UUID] = Field(default_factory=list)
    reject_ids: list[uuid.UUID] = Field(default_factory=list)


# ---------- Donors ----------
class DonorUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    availability: Availability | None = None


class AvailabilityIn(BaseModel):
    availability: Availability


# ---------- Invitations ----------
class InvitationOut(ORM):
    id: uuid.UUID
    request_id: uuid.UUID
    donor_id: uuid.UUID
    status: str
    sent_at: datetime
    responded_at: datetime | None
    response_message: str | None
    response_analysis: dict[str, Any] | None
    # denormalised request info for the donor inbox
    request_blood_group: str
    request_urgency: str
    request_location: str
    request_deadline: datetime
    hospital_name: str
    donor_name: str


class RespondIn(BaseModel):
    response: Literal["accepted", "declined"]
    message: str | None = Field(default=None, max_length=1000)


# ---------- Agents / audit ----------
class AgentRunOut(ORM):
    id: uuid.UUID
    request_id: uuid.UUID | None
    agent_name: str
    status: str
    input_summary: str | None
    output_summary: str | None
    output_data: dict[str, Any] | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None


class TimelineEvent(BaseModel):
    kind: Literal["agent_run", "audit"]
    id: uuid.UUID
    at: datetime
    title: str
    status: str | None = None
    summary: str | None = None
    details: dict[str, Any] | None = None
