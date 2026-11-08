from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError

from app.schemas.schemas import JobCreate, ProfileUpdate, InterviewScheduleRequest
from app.models.models import JobListing, Student
from app.services.eligibility_service import EligibilityService, split_branches


def valid_job(**overrides):
    data = dict(
        role_title="Software Engineer", description="Build and maintain software services for business customers.",
        job_type="Full-time", location="Bengaluru", package_lpa=8.5, min_cgpa=7.0, max_backlogs=1,
        allowed_branches=["Computer Science"], all_branches=False, skills_required="Python, SQL",
        selection_process="Technical and HR interview rounds", num_rounds=1,
        selection_rounds=[{"name":"Technical Interview", "description":"Coding, data structures and problem solving"}],
        deadline=datetime.now(timezone.utc)+timedelta(days=7),
    )
    data.update(overrides)
    return data


def test_branch_scope_must_be_explicit():
    with pytest.raises(ValidationError):
        JobCreate(**valid_job(allowed_branches=[], all_branches=False))
    with pytest.raises(ValidationError):
        JobCreate(**valid_job(allowed_branches=["Computer Science"], all_branches=True))
    all_branch_job = JobCreate(**valid_job(allowed_branches=[], all_branches=True))
    assert all_branch_job.all_branches is True


def test_every_round_requires_a_published_description():
    with pytest.raises(ValidationError):
        JobCreate(**valid_job(selection_rounds=[]))
    with pytest.raises(ValidationError):
        JobCreate(**valid_job(num_rounds=2))
    job = JobCreate(**valid_job())
    assert job.selection_rounds[0]["name"] == "Technical Interview"


def test_identity_and_academic_fields_are_not_directly_editable():
    with pytest.raises(ValidationError):
        ProfileUpdate(name="Changed Name")
    with pytest.raises(ValidationError):
        ProfileUpdate(branch="Mechanical")
    with pytest.raises(ValidationError):
        ProfileUpdate(cgpa=9.5)
    assert ProfileUpdate(phone="+91 98765 43210").phone == "+91 98765 43210"


def test_interview_schedule_requires_valid_mode_and_duration_input():
    data = dict(application_id=1, scheduled_at=datetime.now(timezone.utc)+timedelta(days=1), duration_minutes=30,
                round_type="Technical Interview", mode="Online", location="https://meet.example/room")
    assert InterviewScheduleRequest(**data).round_type == "Technical Interview"
    with pytest.raises(ValidationError):
        InterviewScheduleRequest(**{**data, "mode":"Teleport"})


def test_eligibility_checks_cgpa_backlogs_and_branch_together():
    student = Student(name="Test Student", email="test@example.com", roll_number="T001", branch="Mechanical", cgpa=6.5, active_backlogs=3)
    job = JobListing(role_title="Developer", min_cgpa=7.0, max_backlogs=1, allowed_branches="Computer Science")
    reasons = EligibilityService.academic_reasons(student, job)
    assert len(reasons) == 3
    assert any("CGPA" in x for x in reasons)
    assert any("backlog" in x for x in reasons)
    assert any("Branch" in x for x in reasons)


def test_all_branches_sentinel_is_not_confused_with_empty_selection():
    assert split_branches("*") == []
    assert split_branches("Computer Science,Electronics") == ["Computer Science", "Electronics"]
