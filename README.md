# TalentHub — Campus Placement Management System

TalentHub is a full-stack Campus Placement Management System designed to streamline the campus recruitment process for students, companies, and placement coordinators.

The application uses **React, Vite and Tailwind CSS** for the frontend and **FastAPI, SQLAlchemy and SQLite** for the backend. It provides role-based dashboards, job management, student applications, eligibility validation, placement policy acceptance, offer management, and academic record correction workflows.

## 1. Technology Stack

**Frontend**
- React
- Vite
- Tailwind CSS
- JavaScript

**Backend**
- Python 3.13
- FastAPI
- SQLAlchemy
- SQLite

## 2. Prerequisites

Install the following before running the application:

- Python 3.13
- Node.js 18 or newer
- npm
- Visual Studio Code (recommended)

Internet access is required for the initial installation of dependencies.

**Important:** Python 3.13 is recommended. Use a fresh virtual environment rather than an existing environment created with Python 3.14.

## 3. Project Setup

1. Download or extract the project ZIP file.
2. Open Visual Studio Code.
3. Select **File → Open Folder**.
4. Open the extracted `TalentHub` project folder.
5. Open the VS Code terminal.

The project contains two main folders:

- `backend` — FastAPI application and database.
- `frontend` — React application.

## 4. Run the Backend

Open the first terminal in VS Code.

Navigate to the backend directory:

```powershell
cd backend
```

Create a virtual environment:

```powershell
py -3.13 -m venv .venv
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks virtual environment activation, execute:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate it again:

```powershell
.\.venv\Scripts\Activate.ps1
```

Upgrade pip and install the backend dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Start the backend server:

```powershell
python -m uvicorn main:app --reload --port 8000
```

The backend will run at:

- API: http://127.0.0.1:8000/
- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

Keep this terminal running.

## 5. Run the Frontend

Open a **second terminal** in VS Code. Make sure the first terminal is still running the backend.

Navigate to the frontend directory:

```powershell
cd frontend
```

Install the frontend dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

Open the URL displayed in the terminal. Normally, it is:

http://localhost:5173/

The frontend communicates with the backend running at `http://127.0.0.1:8000`.

## 6. Demo Login Credentials

All demo accounts use the following password:

**Password:** `password123`

| Role | Email |
|---|---|
| Student | rahul@student.talenthub.edu |
| Student | priya@student.talenthub.edu |
| Student | aman@student.talenthub.edu |
| Student | neha@student.talenthub.edu |
| Company — ABC Technologies | hr@abctech.com |
| Company — XYZ Corp | hr@xyzcorp.com |
| Placement Coordinator | coordinator@talenthub.edu |

## 7. Main Features and Workflows

### Student Portal

- View available placement opportunities.
- View detailed job descriptions, package, location, required skills, eligible branches, CGPA and backlog criteria, and application deadlines.
- Read and accept the active Placement Policy before submitting the first application.
- Policy acceptance is required once per policy version, not separately for every job.
- Apply for eligible jobs.
- Track application status and view rejection reasons.
- View published selection-round names and descriptions.
- Edit contact information and skills.
- Submit academic record correction requests for CGPA and active backlogs.
- View issued offers and accept or decline them before the response deadline.

### Company Portal

- Create and manage job postings.
- Specify job descriptions, eligibility criteria, required skills, application deadlines, and eligible branches.
- Publish selection-round names and descriptions for applicants.
- View and review student applications.
- Shortlist applicants or reject applications with a reason.
- Record final selection decisions after completing the selection process.
- Issue offers with package details and response deadlines.
- Track student offer responses.

**Note:** TalentHub does not schedule interview rounds or allocate interview time slots. Companies conduct their selection process separately and record the final decision in the portal.

### Placement Coordinator Portal

- View placement statistics and student records.
- Monitor applications and placement activity.
- Review academic record correction requests.
- Approve or reject requested academic changes.
- Provide reasons when rejecting correction requests.
- View profile audit history.
- Publish updated Placement Policy versions.

## 8. Important Business Rules

- Students must accept the active Placement Policy before applying.
- Acceptance applies to all applications under the same policy version.
- A newly published policy version requires fresh acceptance.
- Student eligibility is validated using CGPA, active backlogs, branch, and other job requirements.
- Students cannot apply after the application deadline.
- Duplicate applications are prevented.
- Academic record changes take effect only after coordinator approval.
- Rejection decisions require a written reason.
- An offer can be issued only after the selection process is marked as completed.
- Students can accept or decline offers before the response deadline.

## 9. Database

TalentHub uses SQLite with SQLAlchemy for database management.

The database is maintained by the backend application. On initial startup, the application initializes the database and prepares demo data, according to the project's database initialization logic.

For a fresh demo environment, stop the backend before resetting its database. Do not delete the database if you need to preserve existing student accounts, applications, or placement records.

## 10. Running Backend Tests

From the backend directory, with the virtual environment activated, run:

```powershell
python -m pytest -q
```

## 11. Project Structure

```text
TalentHub/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   └── services/
│   │
│   ├── tests/
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   └── pages/
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

## 12. Notes

- Run the backend and frontend in separate terminals.
- Start the backend before using the frontend.
- Keep both development servers running while using the application.
- Demo credentials are intended for demonstration purposes only.
- Replace demo credentials, sample records, and the seeded Placement Policy with institution-approved information before production deployment.