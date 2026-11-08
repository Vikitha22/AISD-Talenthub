BRANCHES = [
    "Computer Science",
    "Information Technology",
    "Electronics",
    "Electrical",
    "Mechanical",
    "Civil",
    "Chemical",
]
JOB_TYPES = ["Full-time", "Internship", "Internship + PPO"]
ROUND_TYPES = ["Aptitude Test", "Technical", "Group Discussion", "HR", "Managerial", "Other"]
INTERVIEW_MODES = ["Online", "On-campus"]

# Application lifecycle
APPLIED = "APPLIED"
SHORTLISTED = "SHORTLISTED"
INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
INTERVIEW_CLEARED = "INTERVIEW_CLEARED"
OFFERED = "OFFERED"
ACCEPTED = "ACCEPTED"
DECLINED = "DECLINED"
OFFER_EXPIRED = "OFFER_EXPIRED"
REJECTED = "REJECTED"
WITHDRAWN = "WITHDRAWN"

# Applications that are still "in play" (no final outcome yet)
OPEN_STATUSES = (APPLIED, SHORTLISTED, INTERVIEW_SCHEDULED, INTERVIEW_CLEARED)

# Interview results
PENDING = "PENDING"
PASS = "PASS"
FAIL = "FAIL"
CANCELLED = "CANCELLED"

# Offer states
OFFER_PENDING = "PENDING"
OFFER_ACCEPTED = "ACCEPTED"
OFFER_DECLINED = "DECLINED"
OFFER_EXPIRED_STATE = "EXPIRED"
