"""Request schemas (input validation). Responses are built by app.services.serializers."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.config import MAX_ROUNDS, OFFER_DEFAULT_RESPONSE_DAYS, OFFER_MAX_RESPONSE_DAYS
from app.core.constants import BRANCHES, INTERVIEW_MODES, JOB_TYPES, ROUND_TYPES
from app.core.timeutil import to_naive_utc


def _clean(v: str | None) -> str | None:
    return v.strip() if isinstance(v, str) else v


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def lower(cls, v):
        return v.strip().lower()


class ProfileUpdate(BaseModel):
    """Only contact/skills are directly editable. Academic data uses a review request."""
    phone: Optional[str] = Field(default=None, max_length=15)
    skills: Optional[str] = Field(default=None, max_length=300)

    @field_validator("skills", "phone")
    @classmethod
    def strip(cls, v):
        return _clean(v)

    @field_validator("phone")
    @classmethod
    def phone_ok(cls, v):
        if v and not all(c.isdigit() or c in "+- " for c in v):
            raise ValueError("Phone may contain only digits, spaces, '+' and '-'")
        return v

    @model_validator(mode="after")
    def at_least_one(self):
        if not self.model_fields_set:
            raise ValueError("Send at least one field to update")
        return self


class AcademicUpdateRequestSchema(BaseModel):
    field: Literal["cgpa", "active_backlogs"]
    value: float | int
    @model_validator(mode="after")
    def valid_value(self):
        if self.field == "cgpa" and not 0 <= float(self.value) <= 10:
            raise ValueError("CGPA must be between 0 and 10")
        if self.field == "active_backlogs" and (int(self.value) != self.value or not 0 <= int(self.value) <= 30):
            raise ValueError("Active backlogs must be a whole number between 0 and 30")
        return self


class AcademicReviewRequest(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    note: str = Field(default="", max_length=500)


class JobCreate(BaseModel):
    role_title: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=20, max_length=3000)
    job_type: str = "Full-time"
    location: str = Field(min_length=2, max_length=100)
    package_lpa: float = Field(gt=0, le=500)
    min_cgpa: float = Field(ge=0, le=10)
    max_backlogs: int = Field(ge=0, le=20)
    allowed_branches: list[str] = Field(default_factory=list)
    all_branches: bool = False  # must be explicitly selected
    skills_required: str = Field(default="", max_length=300)
    selection_process: str = Field(default="", max_length=1000)
    selection_rounds: list[dict] = Field(default_factory=list, max_length=6)
    num_rounds: int = Field(default=1, ge=1, le=MAX_ROUNDS)
    deadline: datetime

    @field_validator("role_title", "description", "location", "skills_required", "selection_process")
    @classmethod
    def strip(cls, v):
        return _clean(v)

    @field_validator("job_type")
    @classmethod
    def job_type_ok(cls, v):
        if v not in JOB_TYPES:
            raise ValueError(f"Job type must be one of: {', '.join(JOB_TYPES)}")
        return v

    @field_validator("allowed_branches")
    @classmethod
    def branches_ok(cls, v):
        bad = [b for b in v if b not in BRANCHES]
        if bad:
            raise ValueError(f"Unknown branch(es): {', '.join(bad)}")
        return list(dict.fromkeys(v))

    @field_validator("selection_rounds")
    @classmethod
    def validate_rounds(cls, v):
        cleaned = []
        for i, item in enumerate(v, 1):
            name = str(item.get("name", "")).strip()
            description = str(item.get("description", "")).strip()
            if not name or len(name) > 100 or len(description) < 5 or len(description) > 1000:
                raise ValueError(f"Round {i} needs a name and a description of at least 5 characters")
            cleaned.append({"round_number": i, "name": name, "description": description})
        if cleaned and len(cleaned) != len(v):
            raise ValueError("Invalid interview rounds")
        return cleaned

    @model_validator(mode="after")
    def rounds_match(self):
        if len(self.selection_rounds) != self.num_rounds:
            raise ValueError("Provide a detailed description for every interview round")
        return self

    @model_validator(mode="after")
    def explicit_branch_scope(self):
        if self.all_branches and self.allowed_branches:
            raise ValueError("Choose All branches or selected branches, not both")
        if not self.all_branches and not self.allowed_branches:
            raise ValueError("Select at least one branch or explicitly choose All branches")
        return self

    @field_validator("deadline")
    @classmethod
    def deadline_utc(cls, v):
        return to_naive_utc(v)


class ApplicationCreate(BaseModel):
    job_id: int


class ApplicationStatusUpdate(BaseModel):
    status: Literal["SHORTLISTED", "REJECTED"]
    reason: Optional[str] = Field(default=None, max_length=500)  # mandatory when REJECTED
    note: Optional[str] = Field(default=None, max_length=500)


class InterviewScheduleRequest(BaseModel):
    application_id: int
    scheduled_at: datetime
    duration_minutes: int = 30
    round_type: str
    mode: str
    location: str = Field(min_length=2, max_length=300)  # venue or meeting link
    notes: str = Field(default="", max_length=500)

    @field_validator("scheduled_at")
    @classmethod
    def utc(cls, v):
        return to_naive_utc(v)

    @field_validator("round_type")
    @classmethod
    def rt(cls, v):
        v = v.strip()
        if not 2 <= len(v) <= 100:
            raise ValueError("Round name must contain 2-100 characters")
        return v

    @field_validator("mode")
    @classmethod
    def md(cls, v):
        if v not in INTERVIEW_MODES:
            raise ValueError(f"Mode must be one of: {', '.join(INTERVIEW_MODES)}")
        return v

    @field_validator("location", "notes")
    @classmethod
    def strip(cls, v):
        return _clean(v)


class InterviewRescheduleRequest(BaseModel):
    scheduled_at: datetime
    duration_minutes: Optional[int] = None
    location: Optional[str] = Field(default=None, min_length=2, max_length=300)
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("scheduled_at")
    @classmethod
    def utc(cls, v):
        return to_naive_utc(v)


class InterviewResultRequest(BaseModel):
    result: Literal["PASS", "FAIL"]
    confirm_completed: bool = False
    feedback: str = Field(default="", max_length=500)  # mandatory when FAIL


class OfferCreate(BaseModel):
    application_id: int
    package_lpa: Optional[float] = Field(default=None, gt=0, le=500)  # defaults to the job's package
    respond_within_days: int = Field(default=OFFER_DEFAULT_RESPONSE_DAYS, ge=1, le=OFFER_MAX_RESPONSE_DAYS)


class OfferRespondRequest(BaseModel):
    accept: bool
    note: str = Field(default="", max_length=300)


class PolicyPublish(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    content: str = Field(min_length=50, max_length=20000)


class PolicyAcceptRequest(BaseModel):
    policy_id: int
    agree: bool
