from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.core.timeutil import utcnow
from app.models.models import Company, JobListing, Policy, Student, User

DEMO_PASSWORD = "password123"

POLICY_V1 = """TALENTHUB CAMPUS PLACEMENT POLICY AND AGREEMENT

1. Purpose
This policy governs how students, recruiting companies and the Placement Cell behave during the campus placement process. Every student must read and accept the active Placement Policy once before submitting their first job application. The same accepted version applies to all job applications; a new acceptance is needed only when the Placement Cell publishes a new policy version.

2. Eligibility
(a) Every job lists its own minimum CGPA, maximum number of active backlogs and the branches it is open to. You may apply only if you meet ALL of these criteria on the day you apply.
(b) The system shows the exact reason whenever you are not eligible. The company re-checks your current academic record before shortlisting you.
(c) You must keep your profile accurate. Your name, roll number and branch are institutional records. CGPA and backlog changes require Placement Coordinator verification before they affect eligibility. Giving false academic information can lead to disqualification from all placement activity.

3. Applications and deadlines
(a) Each job has an application deadline. Applications are not possible after it.
(b) You may apply to a job only once.
(c) A company that rejects you, or fails you in an interview round, must record the reason, and you can see it on your dashboard.

4. Interviews
(a) Selection can have several rounds. A round can be scheduled only after the previous round has been passed.
(b) No two students can be given the same time slot by a company, and you will never be double-booked.
(c) Attend every scheduled round on time. If you cannot attend, tell the company's HR and the Placement Cell in advance.

5. Offers
(a) An offer shows its reference number, package and the date by which you must reply. Until you reply it is shown as PENDING.
(b) If you do not accept or decline by that date, the offer EXPIRES automatically and cannot be revived by the system.
(c) Your answer is final: an accepted offer cannot be declined later and a declined offer cannot be accepted later.

6. One-offer rule
(a) A student may accept only ONE offer. When you accept an offer, your other pending offers are closed and your other open applications are withdrawn automatically, and you cannot apply to further jobs.
(b) Think carefully before accepting: the one-offer rule is enforced by the system.

7. Data use
Your profile, applications and results are visible to the Placement Cell. A company can see only the students who applied to its own job listings.

8. Conduct
Be honest and professional with companies and the Placement Cell. Misconduct may lead to removal from the placement process.

By accepting, you confirm that you have read, understood and agree to this policy."""


async def seed_if_empty(db: AsyncSession):
    """Idempotently seed demo data and repair demo logins in an existing database.

    Earlier builds returned as soon as *any* user existed. That left partially seeded
    databases with missing demo accounts (or stale demo passwords). This routine keeps
    existing student academic data intact while ensuring every documented demo login works.
    """
    now = utcnow()
    existing_users = (await db.execute(select(User))).scalars().all()
    existing_students = (await db.execute(select(Student))).scalars().all()
    existing_companies = (await db.execute(select(Company))).scalars().all()

    # Ensure policy v1 exists, but never overwrite a policy already published by a coordinator.
    policy = (await db.execute(select(Policy).where(Policy.version == 1))).scalar_one_or_none()
    if policy is None:
        db.add(Policy(version=1, title="Campus Placement Policy (v1)", content=POLICY_V1, is_active=True))

    companies_by_name = {c.name: c for c in existing_companies}
    for name, description in (
        ("ABC Technologies", "Product-based software company"),
        ("XYZ Corp", "Core engineering & infrastructure company"),
    ):
        if name not in companies_by_name:
            company = Company(name=name, description=description)
            db.add(company)
            companies_by_name[name] = company
    await db.flush()

    students_by_email = {s.email.lower(): s for s in existing_students}
    demo_students = [
        Student(roll_number="CS21001", name="Rahul Sharma", email="rahul@student.talenthub.edu", phone="+91 98765 43210", branch="Computer Science", cgpa=8.2, active_backlogs=1, skills="Python, SQL, React"),
        Student(roll_number="IT21014", name="Priya Nair", email="priya@student.talenthub.edu", phone="+91 98765 43211", branch="Information Technology", cgpa=9.1, active_backlogs=0, skills="Java, Spring, Docker"),
        Student(roll_number="EC21027", name="Aman Verma", email="aman@student.talenthub.edu", phone="+91 98765 43212", branch="Electronics", cgpa=6.4, active_backlogs=3, skills="C, Embedded systems"),
        Student(roll_number="ME21008", name="Neha Iyer", email="neha@student.talenthub.edu", phone="+91 98765 43213", branch="Mechanical", cgpa=7.6, active_backlogs=0, skills="AutoCAD, SolidWorks"),
    ]
    for student in demo_students:
        if student.email.lower() not in students_by_email:
            # Avoid a duplicate roll number if an earlier partial seed created the record.
            by_roll = (await db.execute(select(Student).where(Student.roll_number == student.roll_number))).scalar_one_or_none()
            students_by_email[student.email.lower()] = by_roll or student
            if by_roll is None:
                db.add(student)
    await db.flush()

    # Keep existing job listings; add the standard sample listings only when none exist.
    from app.models.models import JobListing
    any_jobs = (await db.execute(select(JobListing.id).limit(1))).first()
    if not any_jobs:
        abc = companies_by_name["ABC Technologies"]
        xyz = companies_by_name["XYZ Corp"]
        db.add_all([
            JobListing(company_id=abc.id, role_title="Software Developer", job_type="Full-time", location="Bengaluru", description="Full-stack development on our cloud products: design APIs, build web front-ends, write tests and work in a small agile team. Training is provided for the first three months.", package_lpa=8.5, min_cgpa=7.0, max_backlogs=2, allowed_branches="Computer Science,Information Technology,Electronics", skills_required="Python or Java, SQL, basic web development", selection_process="Online technical test followed by HR and managerial interview.", selection_rounds='[{"round_number":1,"name":"Online Technical Test","description":"Coding, aptitude and problem-solving assessment"},{"round_number":2,"name":"HR and Managerial Interview","description":"Communication, teamwork and role-fit discussion"}]', num_rounds=2, deadline=now + timedelta(days=14)),
            JobListing(company_id=abc.id, role_title="QA Engineer", job_type="Full-time", location="Pune", description="Plan and run manual and automated tests for web applications, report defects and help developers reproduce and fix them.", package_lpa=6.0, min_cgpa=6.0, max_backlogs=3, allowed_branches="*", skills_required="Testing fundamentals, attention to detail", selection_process="Testing concepts and a practical exercise.", selection_rounds='[{"round_number":1,"name":"QA Technical Interview","description":"Testing concepts, test-case design and practical defect analysis"}]', num_rounds=1, deadline=now + timedelta(days=10)),
            JobListing(company_id=xyz.id, role_title="Backend Engineer", job_type="Full-time", location="Hyderabad", description="Build and maintain scalable backend services and internal platforms for infrastructure products.", package_lpa=10.0, min_cgpa=8.0, max_backlogs=0, allowed_branches="Computer Science,Information Technology", skills_required="Data structures, backend language, databases, REST APIs", selection_process="Coding assessment followed by system design interview.", selection_rounds='[{"round_number":1,"name":"Coding Assessment","description":"Data structures, algorithms and coding exercise"},{"round_number":2,"name":"System Design Interview","description":"Backend architecture, scalability and technical discussion"}]', num_rounds=2, deadline=now + timedelta(days=21)),
            JobListing(company_id=xyz.id, role_title="Site Engineer Trainee", job_type="Internship + PPO", location="Chennai", description="Support construction and plant sites with measurements, reports and quality checks.", package_lpa=4.8, min_cgpa=6.5, max_backlogs=1, allowed_branches="Civil,Mechanical", skills_required="Site drawings, AutoCAD", selection_process="One technical round.", selection_rounds='[{"round_number":1,"name":"Civil and Site Technical Interview","description":"Site drawings, measurements, safety and AutoCAD fundamentals"}]', num_rounds=1, deadline=now - timedelta(days=2)),
        ])
    await db.flush()

    # Reset the documented demo password for demo identities only. Existing academic
    # records and user data are not overwritten.
    pw = hash_password(DEMO_PASSWORD)
    demo_user_specs = []
    for email, student in students_by_email.items():
        if email in {"rahul@student.talenthub.edu", "priya@student.talenthub.edu", "aman@student.talenthub.edu", "neha@student.talenthub.edu"}:
            demo_user_specs.append((email, "STUDENT", student.name, student.id, None))
    for company_name, email in (("ABC Technologies", "hr@abctech.com"), ("XYZ Corp", "hr@xyzcorp.com")):
        company = companies_by_name[company_name]
        demo_user_specs.append((email, "COMPANY", company.name, None, company.id))
    demo_user_specs.append(("coordinator@talenthub.edu", "COORDINATOR", "Placement Coordinator", None, None))
    users_by_email = {u.email.lower(): u for u in existing_users}
    for email, role, display_name, student_id, company_id in demo_user_specs:
        user = users_by_email.get(email)
        if user is None:
            user = User(email=email, hashed_password=pw, role=role, display_name=display_name, student_id=student_id, company_id=company_id)
            db.add(user)
        else:
            user.hashed_password = pw
            user.role = role
            user.display_name = display_name
            user.student_id = student_id
            user.company_id = company_id
    await db.commit()
