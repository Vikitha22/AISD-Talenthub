from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

from app.core.timeutil import utcnow

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # STUDENT, COMPANY, COORDINATOR
    display_name = Column(String, nullable=False, default="")
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    roll_number = Column(String, unique=True, index=True, nullable=False)  # institutional identity
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, default="")
    branch = Column(String, nullable=False)
    cgpa = Column(Float, nullable=False)
    active_backlogs = Column(Integer, default=0, nullable=False)
    skills = Column(String, default="")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    applications = relationship("Application", back_populates="student")


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")

    jobs = relationship("JobListing", back_populates="company")


class JobListing(Base):
    __tablename__ = "job_listings"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    role_title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    job_type = Column(String, nullable=False, default="Full-time")
    location = Column(String, nullable=False, default="")
    package_lpa = Column(Float, nullable=False, default=0.0)
    min_cgpa = Column(Float, nullable=False, default=0.0)
    max_backlogs = Column(Integer, nullable=False, default=0)
    allowed_branches = Column(String, nullable=False, default="")  # comma separated; "" = all branches
    skills_required = Column(String, default="")
    selection_process = Column(Text, default="")
    selection_rounds = Column(Text, default="[]", nullable=False)  # JSON list: [{name, description}]
    num_rounds = Column(Integer, nullable=False, default=1)
    deadline = Column(DateTime, nullable=False)  # applications close at this UTC instant
    created_at = Column(DateTime, default=utcnow)

    company = relationship("Company", back_populates="jobs")
    applications = relationship("Application", back_populates="job")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("student_id", "job_id", name="uq_student_job"),)
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("job_listings.id"), nullable=False)
    status = Column(String, default="APPLIED", nullable=False)
    rejection_reason = Column(Text, nullable=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=True)  # policy version accepted when applying
    applied_at = Column(DateTime, default=utcnow)
    status_updated_at = Column(DateTime, default=utcnow)

    student = relationship("Student", back_populates="applications")
    job = relationship("JobListing", back_populates="applications")
    interviews = relationship("Interview", back_populates="application", order_by="Interview.round_number")
    offer = relationship("Offer", back_populates="application", uselist=False)
    events = relationship("ApplicationEvent", back_populates="application", order_by="ApplicationEvent.id")


class ApplicationEvent(Base):
    """Immutable audit trail: every status change is recorded with who did it and why."""
    __tablename__ = "application_events"
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), index=True, nullable=False)
    status = Column(String, nullable=False)
    note = Column(Text, default="")
    actor_role = Column(String, default="SYSTEM")
    created_at = Column(DateTime, default=utcnow)

    application = relationship("Application", back_populates="events")


class Interview(Base):
    __tablename__ = "interviews"
    __table_args__ = (UniqueConstraint("application_id", "round_number", name="uq_app_round"),)
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), index=True, nullable=False)
    round_number = Column(Integer, nullable=False)
    round_type = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    location = Column(String, nullable=False)  # venue or meeting link
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=30)
    result = Column(String, default="PENDING", nullable=False)  # PENDING, PASS, FAIL, CANCELLED
    feedback = Column(Text, default="")
    notes = Column(Text, default="")

    application = relationship("Application", back_populates="interviews")


class Offer(Base):
    __tablename__ = "offers"
    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String, unique=True, index=True)  # e.g. OFR-2026-00007
    application_id = Column(Integer, ForeignKey("applications.id"), unique=True, nullable=False)
    package_lpa = Column(Float, nullable=False)
    status = Column(String, default="PENDING", nullable=False)  # PENDING, ACCEPTED, DECLINED, EXPIRED
    issued_at = Column(DateTime, default=utcnow)
    respond_by = Column(DateTime, nullable=False)
    responded_at = Column(DateTime, nullable=True)
    response_note = Column(Text, default="")

    application = relationship("Application", back_populates="offer")


class Policy(Base):
    __tablename__ = "policies"
    id = Column(Integer, primary_key=True)
    version = Column(Integer, nullable=False, unique=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    published_at = Column(DateTime, default=utcnow)


class PolicyAcceptance(Base):
    __tablename__ = "policy_acceptances"
    __table_args__ = (UniqueConstraint("student_id", "policy_id", name="uq_student_policy"),)
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    accepted_at = Column(DateTime, default=utcnow)


class AcademicUpdateRequest(Base):
    __tablename__ = "academic_update_requests"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    field = Column(String, nullable=False)  # cgpa or active_backlogs
    old_value = Column(String, nullable=False)
    requested_value = Column(String, nullable=False)
    status = Column(String, default="PENDING", nullable=False)
    coordinator_note = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)
    reviewed_at = Column(DateTime, nullable=True)


class ProfileAudit(Base):
    __tablename__ = "profile_audit"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    field = Column(String, nullable=False)
    old_value = Column(String, default="")
    new_value = Column(String, default="")
    changed_at = Column(DateTime, default=utcnow)
